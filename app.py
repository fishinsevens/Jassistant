# backend/app.py
import os
import logging
import time
import atexit
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify, send_from_directory
import db_manager
import api_handler
import webhook_handler

# 尝试导入fcntl，在Windows环境中可能不可用
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

def _ensure_startup_log_once(app, process_type="web"):
    """
    确保启动日志只被记录一次的改进机制

    Args:
        app: Flask应用实例
        process_type: 进程类型，"web" 或 "scheduler"

    Returns:
        bool: 是否应该记录启动日志
    """
    current_pid = os.getpid()
    lock_dir = 'logs'
    pid_file_path = os.path.join(lock_dir, f'startup_{process_type}.pid')

    def cleanup_pid_file():
        """清理PID文件"""
        try:
            if os.path.exists(pid_file_path):
                os.remove(pid_file_path)
        except Exception as e:
            app.logger.warning(f"清理PID文件失败: {e}")

    # 注册退出时清理函数
    atexit.register(cleanup_pid_file)

    try:
        # 检查是否存在旧的PID文件
        if os.path.exists(pid_file_path):
            try:
                with open(pid_file_path, 'r') as f:
                    old_pid = int(f.read().strip())

                # 检查旧进程是否还在运行
                try:
                    os.kill(old_pid, 0)  # 发送信号0检查进程是否存在
                    # 进程仍在运行，不应记录启动日志
                    app.logger.debug(f"{process_type}进程 {old_pid} 仍在运行，跳过启动日志")
                    return False
                except OSError:
                    # 进程不存在，删除旧的PID文件
                    app.logger.debug(f"清理过期的{process_type}进程PID文件: {old_pid}")
                    os.remove(pid_file_path)
            except (ValueError, IOError) as e:
                app.logger.warning(f"读取PID文件失败: {e}，将重新创建")
                try:
                    os.remove(pid_file_path)
                except:
                    pass

        # 尝试创建新的PID文件（原子操作）
        temp_pid_file = f"{pid_file_path}.tmp.{current_pid}"
        try:
            with open(temp_pid_file, 'w') as f:
                f.write(str(current_pid))
                f.flush()
                os.fsync(f.fileno())  # 强制写入磁盘

            # 原子性地重命名文件
            os.rename(temp_pid_file, pid_file_path)
            app.logger.debug(f"成功创建{process_type}进程PID文件: {current_pid}")
            return True

        except Exception as e:
            # 清理临时文件
            try:
                if os.path.exists(temp_pid_file):
                    os.remove(temp_pid_file)
            except:
                pass

            app.logger.warning(f"创建PID文件失败: {e}")
            return False

    except Exception as e:
        app.logger.error(f"启动日志控制机制异常: {e}")
        return False

def create_app():
    """应用工厂函数，创建Flask应用实例"""
    # 确保必要的目录存在
    os.makedirs('logs', exist_ok=True)
    os.makedirs('db', exist_ok=True)
    os.makedirs('settings', exist_ok=True)

    # 配置日志
    log_file_path = os.path.join('logs', 'app.log')
    file_handler = RotatingFileHandler(log_file_path, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))

    # 配置Flask应用，指定静态文件目录
    static_folder = os.path.join(os.path.dirname(__file__), 'static')
    app = Flask(__name__, static_folder=static_folder, static_url_path='')
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)

    # 使用改进的启动日志控制机制
    should_log_startup = _ensure_startup_log_once(app, "web")

    if should_log_startup:
        from config_utils import VERSION
        app.logger.info(f"=== Jassistant v{VERSION} Web服务启动成功 ===")
        app.logger.info(f"Web服务已在端口34711启动，PID: {os.getpid()}")

    # 初始化数据库
    with app.app_context():
        db_manager.init_db()
        if should_log_startup:
            app.logger.info("数据库初始化完成")

    # 初始化性能监控系统
    try:
        from monitoring import monitoring_system
        monitoring_system.start()
        if should_log_startup:
            app.logger.info("性能监控系统已启动")
    except Exception as e:
        app.logger.error(f"启动监控系统失败: {e}")

    # Web进程不再初始化调度器，调度器由独立进程管理
    if should_log_startup:
        app.logger.info("Web服务初始化完成，调度器由独立进程管理")
    
    # 配置API密钥
    app.config['CID_API_KEY'] = os.environ.get('CID_API_KEY')
    app.config['CID_API_URL'] = os.environ.get('CID_API_URL')
    
    # 注册API路由
    api_handler.init_app(app)
    
    # 静态文件路由
    @app.route('/')
    def index():
        return send_from_directory(app.static_folder, 'index.html')
    
    @app.route('/<path:path>')
    def static_files(path):
        # 如果是API请求，返回404
        if path.startswith('api/'):
            return jsonify(error="The requested API endpoint was not found on the server"), 404
        
        # 检查文件是否存在
        file_path = os.path.join(app.static_folder, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return send_from_directory(app.static_folder, path)
        else:
            # 对于React路由，返回index.html
            return send_from_directory(app.static_folder, 'index.html')
    
    # 错误处理
    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith('/api/'):
            return jsonify(error="The requested API endpoint was not found on the server"), 404
        return send_from_directory(app.static_folder, 'index.html')
    
    # Webhook处理
    @app.route('/api/webhook', methods=['POST'])
    def emby_webhook():
        data = request.json
        app.logger.info(f"接收到 Webhook 事件: {data.get('Event')}")
        if data and data.get('Event') == 'library.new':
            try:
                with app.app_context():
                    result = webhook_handler.process_new_item(data)
                app.logger.info(f"处理完成: {result['message']}")
                return jsonify(result), 200
            except Exception as e:
                app.logger.error(f"处理 Webhook 时发生错误: {e}", exc_info=True)
                return jsonify({"success": False, "message": str(e)}), 500
        return jsonify({"success": True, "message": "Event received but not processed."}), 200
    
    return app

# 全局Flask应用实例
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=34711, debug=True)
