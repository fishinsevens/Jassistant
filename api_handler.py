# backend/api_handler.py
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
import shutil
import xml.etree.ElementTree as ET
import subprocess
import signal
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from db_manager import get_db_connection
import image_processor
from config_utils import get_settings, save_settings, get_restart_required_settings
from nfo_parser import parse_nfo_file
from notification_sender import send_test_notification
import uuid
import tempfile
from werkzeug.utils import secure_filename
import urllib.parse
import re
from bs4 import BeautifulSoup
import time
import threading

# 导入工具类
from utils import (is_safe_path as utils_is_safe_path, get_safe_filename,
                  ensure_dir_exists, HTTP_HEADERS, safe_rename, safe_copy, safe_delete)

# 导入性能优化模块
from db_performance import db_performance_optimizer
from cache_manager import cache_manager
from monitoring import monitoring_system
from performance_test import performance_tester

# 创建优化的HTTP Session，支持连接复用和Keep-Alive
def create_optimized_session():
    """创建优化的requests Session，支持连接池和重试"""
    session = requests.Session()

    # 配置重试策略
    retry_strategy = Retry(
        total=2,  # 总重试次数
        backoff_factor=0.5,  # 重试间隔
        status_forcelist=[429, 500, 502, 503, 504],  # 需要重试的状态码
    )

    # 配置HTTP适配器，支持连接池
    adapter = HTTPAdapter(
        pool_connections=10,  # 连接池大小
        pool_maxsize=20,      # 每个连接池的最大连接数
        max_retries=retry_strategy,
        pool_block=False      # 非阻塞模式
    )

    # 为HTTP和HTTPS配置适配器
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # 启用Keep-Alive（默认已启用，但明确设置）
    session.headers.update({
        'Connection': 'keep-alive',
        'Keep-Alive': 'timeout=30, max=100'
    })

    return session

# 创建全局Session实例，用于链接验证
_http_session = create_optimized_session()

# DMM域名缓存
_dmm_domain_cache = {
    'status': None,  # 'available', 'unavailable', None
    'last_check': None,
    'cache_duration': 300  # 5分钟缓存
}

def check_dmm_domain_availability():
    """检查DMM域名可用性 - 跳过检测，直接返回可用"""
    # 用户确认网站可以访问，跳过域名检测以避免不必要的延迟
    return True

def is_dmm_url(url):
    """判断是否为DMM链接"""
    return url and 'awsimgsrc.dmm.co.jp' in url

api = Blueprint('api', __name__)
# 改为从配置中获取媒体根路径
def get_media_root():
    return get_settings().get('media_root', '/weiam')

# 封面缓存相关函数
def get_cover_cache_dir():
    """获取封面缓存目录路径"""
    settings = get_settings()
    # 默认在cover_cache目录下（与logs、db等目录同级）
    cache_dir = settings.get('cover_cache_dir', 'cover_cache')
    # 确保目录存在
    ensure_dir_exists(cache_dir)
    return cache_dir

def copy_to_cover_cache(poster_path, strm_name):
    """将封面图片复制到缓存目录"""
    if not poster_path or not strm_name:
        current_app.logger.warning(f"缓存封面失败: 无效的参数，poster_path={poster_path}, strm_name={strm_name}")
        return None
        
    # 检查源文件是否存在
    if not os.path.exists(poster_path):
        current_app.logger.warning(f"缓存封面失败: 源文件不存在 - {poster_path}")
        return None
        
    if not os.path.isfile(poster_path):
        current_app.logger.warning(f"缓存封面失败: 源路径不是文件 - {poster_path}")
        return None
    
    try:
        # 确保目标目录存在
        cache_dir = get_cover_cache_dir()
        
        # 使用strm_name的完整路径生成一个唯一的文件名，确保不同路径的同名影片不会冲突
        # 使用路径信息计算哈希，作为文件名前缀，保留原始番号作为文件名主体部分
        import hashlib
        # 计算strm_name (通常是路径) 的哈希值的前8位作为前缀
        name_hash = hashlib.md5(strm_name.encode('utf-8')).hexdigest()[:8]
        # 从strm_name中提取番号部分作为文件名主体
        base_name = os.path.basename(strm_name)
        if '.' in base_name:
            base_name = base_name.split('.')[0]  # 移除文件扩展名
            
        # 结合哈希和番号创建安全的文件名
        safe_name = f"{name_hash}_{get_safe_filename(base_name)}"
        current_app.logger.debug(f"生成缓存文件名: {safe_name} (来源: {strm_name})")
            
        dest_path = os.path.join(cache_dir, f"{safe_name}.jpg")
        
        # 如果目标文件已存在且最近更新过（1小时内），跳过复制
        if os.path.exists(dest_path):
            source_mtime = os.path.getmtime(poster_path)
            dest_mtime = os.path.getmtime(dest_path)
            
            # 如果目标文件比源文件新，或者不超过1小时，则不更新
            one_hour = 60 * 60  # 秒数
            if dest_mtime >= source_mtime or (time.time() - dest_mtime) < one_hour:
                current_app.logger.debug(f"缓存封面已存在且较新: {safe_name}")
                return dest_path
        
        # 使用安全复制函数        
        success, error = safe_copy(poster_path, dest_path)
        if success:
            current_app.logger.info(f"已缓存封面: {safe_name}")
            return dest_path
        else:
            current_app.logger.error(f"缓存封面失败: {error}")
            return None
    except Exception as e:
        current_app.logger.error(f"缓存封面失败: {str(e)}")
        return None

def clean_cover_cache(max_covers=100):
    """清理多余的封面缓存，保留与数据库中最新项目匹配的缓存"""
    try:
        # 确保max_covers是整数
        if isinstance(max_covers, str):
            try:
                max_covers = int(max_covers)
            except ValueError:
                current_app.logger.error(f"max_covers参数格式错误: '{max_covers}'，应为整数")
                max_covers = 24  # 使用默认值
        
        cache_dir = get_cover_cache_dir()
        # 单次检查目录是否存在且是目录
        if not os.path.isdir(cache_dir):
            return
        
        # 先获取所有缓存的封面文件
        cache_files = {}
        for filename in os.listdir(cache_dir):
            if filename.endswith('.jpg'):
                file_path = os.path.join(cache_dir, filename)
                # 确保是文件而非目录
                if os.path.isfile(file_path):
                    cache_files[filename] = file_path
        
        # 如果没有缓存文件，直接返回
        if not cache_files:
            current_app.logger.debug("没有封面缓存文件，无需清理")
            return
        
        # 获取最新的项目列表
        latest_items = _get_latest_high_quality_items(max_covers)
        
        # 为每个项目生成可能的缓存文件名列表（包括新旧命名方式）
        to_keep_filenames = set()
        
        for item in latest_items:
            strm_name = item.get('strm_name')
            if not strm_name:
                continue
            
            # 新命名方式
            import hashlib
            name_hash = hashlib.md5(strm_name.encode('utf-8')).hexdigest()[:8]
            base_name = os.path.basename(strm_name)
            if '.' in base_name:
                base_name = base_name.split('.')[0]
                
            safe_name = f"{name_hash}_{get_safe_filename(base_name)}"
            new_filename = f"{safe_name}.jpg"
            to_keep_filenames.add(new_filename)
            
            # 旧命名方式
            old_safe_name = get_safe_filename(strm_name)
            old_filename = f"{old_safe_name}.jpg"
            to_keep_filenames.add(old_filename)
        
        # 找出需要删除的文件
        to_delete = []
        for filename, filepath in cache_files.items():
            if filename not in to_keep_filenames:
                to_delete.append(filepath)
        
        # 如果没有需要删除的文件，返回
        if not to_delete:
            current_app.logger.debug(f"所有缓存文件({len(cache_files)})与最新项目匹配，无需清理")
            return
        
        # 删除不在保留列表中的缓存文件
        deleted_count = 0
        for path in to_delete:
            success, _ = safe_delete(path)
            if success:
                deleted_count += 1
                current_app.logger.debug(f"已删除不匹配的封面缓存: {os.path.basename(path)}")
        
        if deleted_count > 0:
            current_app.logger.info(f"已清理封面缓存: 删除了{deleted_count}个不匹配当前项目的文件")
            
    except Exception as e:
        current_app.logger.error(f"封面缓存清理过程出错: {str(e)}", exc_info=True)
        # 不抛出异常，避免影响主要功能

def manage_cover_cache():
    """管理封面缓存，确保缓存不超过设置的数量"""
    settings = get_settings()
    # 确保latest_movies_count是整数
    try:
        max_covers = int(settings.get('latest_movies_count', 24))
    except (TypeError, ValueError):
        max_covers = 24  # 使用默认值
        
    current_app.logger.debug(f"准备清理封面缓存，保留最新{max_covers}个")
    clean_cover_cache(max_covers)

def get_cached_cover_path(strm_name):
    """获取缓存的封面路径，如果存在"""
    if not strm_name:
        return None
    
    try:
        cache_dir = get_cover_cache_dir()
        
        # 使用与copy_to_cover_cache相同的逻辑生成文件名
        import hashlib
        name_hash = hashlib.md5(strm_name.encode('utf-8')).hexdigest()[:8]
        base_name = os.path.basename(strm_name)
        if '.' in base_name:
            base_name = base_name.split('.')[0]
            
        safe_name = f"{name_hash}_{get_safe_filename(base_name)}"
        cached_path = os.path.join(cache_dir, f"{safe_name}.jpg")
        
        if os.path.exists(cached_path):
            return cached_path
            
        # 向后兼容：尝试旧的命名方式
        old_safe_name = get_safe_filename(strm_name)
        old_cached_path = os.path.join(cache_dir, f"{old_safe_name}.jpg")
        if os.path.exists(old_cached_path):
            current_app.logger.debug(f"找到旧格式的缓存文件: {old_safe_name}")
            return old_cached_path
            
    except Exception as e:
        current_app.logger.error(f"查找缓存封面失败: {str(e)}")
    
    return None

class ScrapeError(Exception):
    """用于抓取过程中的错误处理"""
    pass

def scrape_cid(bangou: str) -> str:
    """
    从 avbase.net 搜索并解析出 CID
    """
    search_url = f"https://www.avbase.net/works?q={urllib.parse.quote(bangou)}"
    current_app.logger.info(f"正在访问: {search_url}")
    try:
        response = requests.get(search_url, headers=HTTP_HEADERS, timeout=20)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'lxml')
        
        fanza_img = soup.find('img', alt='fanza')
        
        if not fanza_img:
            raise ScrapeError(f"在AVBase页面中未找到 'fanza' 图标 (可能无此番号记录或页面结构已更改)")
            
        fanza_anchor = fanza_img.find_parent('a')
        if not fanza_anchor or not fanza_anchor.has_attr('href'):
            raise ScrapeError("找到了'fanza'图标，但未能找到其包含链接的父标签")
            
        dmm_url_encoded = fanza_anchor['href']
        dmm_url_decoded = urllib.parse.unquote(dmm_url_encoded)
        
        match = re.search(r'cid=([a-zA-Z0-9_]+)', dmm_url_decoded)
        if not match:
            raise ScrapeError(f"在解码后的链接中未能解析出CID: {dmm_url_decoded}")
            
        found_cid = match.group(1)
        current_app.logger.info(f"成功找到CID: {found_cid}")
        return found_cid
        
    except requests.exceptions.RequestException as e:
        raise ScrapeError(f"网络请求失败: {e}")

# 添加新的API端点用于手动获取CID信息
@api.route('/get-manual-cid-info', methods=['GET'])
def get_manual_cid_info():
    bangou = request.args.get('bangou')
    if not bangou: return jsonify({"success": False, "message": "需要提供番号"}), 400
    
    try:
        # 使用scrape_cid获取CID
        cid = scrape_cid(bangou)
        
        if not cid:
            return jsonify({"success": False, "message": "未找到CID"}), 404
        
        # 与 get_dmm_info 一样构造结果
        parts = cid.split('00')
        code = parts[0] + parts[-1].zfill(5) if len(parts) > 1 else cid
        

        
        result = {
            "cid": cid,
            "rule_info": {"manual": True},
            "wallpaper_url": {"url": f"https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/{code}/{code}pl.jpg"},
            "cover_url": {"url": f"https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/{code}/{code}ps.jpg"}
        }
        
        return jsonify({"success": True, "results": [result]})
        
    except ScrapeError as e:
        current_app.logger.error(f"手动获取CID失败: {e}")
        return jsonify({"success": False, "message": f"获取CID失败: {e}"}), 404
    except Exception as e:
        current_app.logger.error(f"手动获取CID时发生错误: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"处理请求失败: {e}"}), 500

def is_safe_path(path):
    """
    检查请求路径是否在允许的媒体根目录内的包装函数
    
    Args:
        path: 要检查的路径
        
    Returns:
        bool: 如果路径安全则返回True，否则返回False
    """
    return utils_is_safe_path(path, get_media_root())

@api.route('/settings', methods=['GET'])
def get_settings_route(): 
    """获取设置，并标记哪些设置需要重启"""
    settings = get_settings()
    restart_required = get_restart_required_settings()
    
    # 添加需要重启的设置标记
    return jsonify({
        "settings": settings,
        "restart_required_settings": restart_required
    })

@api.route('/settings', methods=['POST'])
def save_settings_route():
    """保存设置，并返回是否需要重启的信息"""
    new_settings = request.json
    
    # 获取当前设置，用于比较变化
    current_settings = get_settings()
    
    # 保存设置
    success, message, restart_needed = save_settings(new_settings, current_settings)
    
    if success:
        # 更新日志级别，这是唯一一个可以不重启就生效的"需要重启"的设置
        if 'log_level' in new_settings:
            log_level_str = new_settings.get('log_level', 'INFO').upper()
            new_level = getattr(logging, log_level_str, logging.INFO)
            current_app.logger.setLevel(new_level)
            for handler in current_app.logger.handlers: 
                handler.setLevel(new_level)
            current_app.logger.info(f"日志级别已更新为: {log_level_str}")
        
        return jsonify({
            "success": True, 
            "message": message,
            "restart_needed": restart_needed
        })
    
    return jsonify({"success": False, "message": message}), 500

@api.route('/test-notification', methods=['POST'])
def test_notification_route():
    """测试通知发送功能并返回详细结果"""
    try:
        with current_app.app_context():
            # 获取当前设置以记录日志
            settings = get_settings()
            notification_api_url = settings.get('notification_api_url', '')
            notification_type = settings.get('notification_type', 'custom')

            # 记录测试开始日志
            current_app.logger.info(f"开始测试{notification_type}类型通知发送，"
                               f"API地址: {notification_api_url if notification_type == 'custom' else 'telegram'}")
            
            # 进行网络连接测试
            if notification_type == 'custom':
                host = notification_api_url.split('://')[1].split(':')[0].split('/')[0] if '://' in notification_api_url else notification_api_url
                port = 5400  # 默认端口，可能需要从URL中解析
                try:
                    parts = notification_api_url.split('://')[1].split(':', 1)
                    if len(parts) > 1:
                        port_str = parts[1].split('/', 1)[0]
                        if port_str.isdigit():
                            port = int(port_str)
                except Exception as e:
                    current_app.logger.warning(f"从URL解析端口失败: {e}, 使用默认端口5400")
                
                # 进行连接测试
                current_app.logger.info(f"测试连接到主机: {host}:{port}")
                import socket
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(5)
                    result = s.connect_ex((host, port))
                    if result == 0:
                        current_app.logger.info(f"连接测试成功: {host}:{port} 可访问")
                    else:
                        current_app.logger.warning(f"连接测试失败: {host}:{port} 不可访问，错误码: {result}")
                except Exception as e:
                    current_app.logger.warning(f"连接测试失败: {e}")
                finally:
                    s.close()
            
            # --- 调用专用的测试函数 ---
            send_test_notification()
            return jsonify({"success": True, "message": "测试通知已发送，请检查您的通知服务。"})
    except requests.exceptions.Timeout as e:
        error_msg = f"发送测试通知超时: {e}"
        current_app.logger.error(error_msg, exc_info=True)
        return jsonify({"success": False, "message": error_msg}), 500
    except requests.exceptions.ConnectionError as e:
        error_msg = f"发送测试通知连接失败: {e}"
        current_app.logger.error(error_msg, exc_info=True)
        return jsonify({"success": False, "message": error_msg}), 500
    except ValueError as e:
        error_msg = f"通知配置错误: {e}"
        current_app.logger.error(error_msg, exc_info=True)
        return jsonify({"success": False, "message": error_msg}), 400
    except Exception as e:
        error_msg = f"发送测试通知失败: {e}"
        current_app.logger.error(error_msg, exc_info=True)
        return jsonify({"success": False, "message": error_msg}), 500

@api.route('/latest-items')
def get_latest_items():
    settings = get_settings()
    count = settings.get('latest_movies_count', 24)
    
    # 获取最新的高画质项目
    items_list = _get_latest_high_quality_items(count)
    
    # 处理封面缓存
    use_cache = settings.get('use_cover_cache', True)  # 默认启用缓存
    
    if use_cache:
        for item in items_list:
            strm_name = item.get('strm_name')
            poster_path = item.get('poster_path')
            
            if strm_name and poster_path:
                # 检查是否已有缓存
                cached_path = get_cached_cover_path(strm_name)
                
                if not cached_path:
                    # 缓存不存在，则创建
                    cached_path = copy_to_cover_cache(poster_path, strm_name)
                
                if cached_path:
                    # 使用缓存路径替换原始路径
                    item['original_poster_path'] = poster_path  # 保留原始路径
                    
                    # 确保路径格式为 'cover_cache/文件名.jpg'
                    # 注意：这里不需要再次调用secure_filename，因为copy_to_cover_cache和get_cached_cover_path已经处理过了
                    item['poster_path'] = os.path.join('cover_cache', os.path.basename(cached_path))
                    
                    # 记录调试信息
                    current_app.logger.debug(f"使用缓存封面: {item['poster_path']} (原路径: {poster_path})")
        
        # 管理缓存，删除多余的
        manage_cover_cache()
    
    return jsonify(items_list)

@api.route('/low-quality-items', methods=['GET'])
def get_low_quality_items():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 10
        offset = (page - 1) * per_page
        conn = get_db_connection()
        query = "SELECT m.id, m.item_path, m.bangou, m.title, p.poster_path, p.poster_status, p.fanart_status FROM movies m JOIN pictures p ON m.id = p.movie_id WHERE p.poster_status = '低画质' OR p.fanart_status = '低画质' ORDER BY m.created_at DESC LIMIT ? OFFSET ?"
        items = conn.execute(query, (per_page, offset)).fetchall()
        total_query = "SELECT COUNT(m.id) FROM movies m JOIN pictures p ON m.id = p.movie_id WHERE p.poster_status = '低画质' OR p.fanart_status = '低画质'"
        total = conn.execute(total_query).fetchone()[0]
        conn.close()
        
        # 恢复原始的返回格式，保持与前端的兼容性
        return jsonify({
            "items": [dict(row) for row in items], 
            "total": total, 
            "page": page, 
            "per_page": per_page, 
            "has_more": total > page * per_page
        })
    except Exception as e:
        current_app.logger.error(f"获取低画质项目失败: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": f"获取低画质项目失败: {str(e)}"}), 500

@api.route('/get-dmm-info', methods=['GET'])
def get_dmm_info():
    bangou = request.args.get('bangou')
    if not bangou: return jsonify({"success": False, "message": "需要提供番号"}), 400
    api_url = current_app.config['CID_API_URL']
    api_key = current_app.config['CID_API_KEY']
    try:
        response = requests.get(api_url, params={'bangou': bangou}, headers={'X-API-KEY': api_key}, timeout=15)
        response.raise_for_status()
        cid_data = response.json()
        if not cid_data.get("success") or not cid_data.get("results"): return jsonify({"success": False, "message": "未找到CID"}), 404
    except requests.RequestException as e: return jsonify({"success": False, "message": f"查询CID失败: {e}"}), 500
    results = []
    for res in cid_data.get("results", []):
        cid = res.get("cid")
        if not cid: continue
        parts = cid.split('00')
        code = parts[0] + parts[-1].zfill(5) if len(parts) > 1 else cid

        results.append({"cid": cid, "rule_info": res.get("rule_info"), "wallpaper_url": {"url": f"https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/{code}/{code}pl.jpg"}, "cover_url": {"url": f"https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/{code}/{code}ps.jpg"},})
    return jsonify({"success": True, "results": results})

def get_cached_verification(url):
    """从缓存中获取链接验证结果"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 查询缓存（永久有效，除非强制刷新）
        cursor.execute("""
            SELECT status_code, is_valid, cid
            FROM link_verification_cache
            WHERE url = ?
        """, (url,))

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                "url": url,
                "status_code": result[0],
                "valid": bool(result[1]),
                "cid": result[2]
            }
        return None
    except Exception as e:
        current_app.logger.error(f"获取缓存失败: {e}")
        return None

def cache_verification_result(url, status_code, is_valid, cid=None):
    """缓存链接验证结果（永久有效）"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO link_verification_cache
            (url, cid, status_code, is_valid, verified_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (url, cid, status_code, is_valid))

        conn.commit()
        conn.close()

    except Exception as e:
        current_app.logger.error(f"缓存验证结果失败: {e}")

@api.route('/clear-link-cache', methods=['POST'])
def clear_link_cache():
    """清除链接验证缓存"""
    try:
        data = request.get_json()
        if data and 'url' in data:
            # 清除特定URL的缓存
            url = data['url']
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM link_verification_cache WHERE url = ?", (url,))
            conn.commit()
            conn.close()
            return jsonify({"success": True, "message": f"已清除 {url} 的缓存"})
        else:
            # 清除所有缓存
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM link_verification_cache")
            conn.commit()
            conn.close()

            # 同时清除DMM域名缓存
            global _dmm_domain_cache
            _dmm_domain_cache['status'] = None
            _dmm_domain_cache['last_check'] = None

            return jsonify({"success": True, "message": "已清除所有链接验证缓存和DMM域名缓存"})
    except Exception as e:
        current_app.logger.error(f"清除缓存失败: {e}")
        return jsonify({"success": False, "message": f"清除缓存失败: {e}"}), 500

@api.route('/clear-dmm-domain-cache', methods=['POST'])
def clear_dmm_domain_cache():
    """清除DMM域名缓存"""
    try:
        global _dmm_domain_cache
        _dmm_domain_cache['status'] = None
        _dmm_domain_cache['last_check'] = None

        return jsonify({
            "success": True,
            "message": "已清除DMM域名缓存"
        })
    except Exception as e:
        current_app.logger.error(f"清除DMM域名缓存失败: {e}")
        return jsonify({"success": False, "message": f"清除DMM域名缓存失败: {e}"}), 500

@api.route('/verify-links', methods=['POST'])
def verify_links():
    """
    批量验证链接有效性
    接收链接数组，返回每个链接的验证状态
    支持强制刷新缓存
    """
    try:
        data = request.get_json()
        if not data or 'links' not in data:
            return jsonify({"success": False, "message": "需要提供links数组"}), 400

        links = data['links']
        force_refresh = data.get('force_refresh', False)  # 是否强制刷新缓存
        cid = data.get('cid')  # 可选的CID参数

        if not isinstance(links, list):
            return jsonify({"success": False, "message": "links必须是数组"}), 400

        def verify_single_link(url):
            """验证单个链接的有效性，支持HTTP缓存协商和DMM域名缓存"""



            # DMM域名优化：如果是DMM链接且域名不可用，直接返回失败
            if is_dmm_url(url) and not check_dmm_domain_availability():
                current_app.logger.debug(f"🚫 DMM域名不可用，跳过验证: {url}")
                return {
                    "url": url,
                    "status_code": 0,
                    "valid": False,
                    "error": "DMM域名不可用"
                }

            # 检查缓存，获取之前的缓存协商头
            cached_result = get_cached_verification(url)

            if not force_refresh and cached_result:
                # 如果不是强制刷新且有缓存，直接返回（永久有效）
                return cached_result

            try:
                try:
                    # 使用4秒超时，适合DMM服务器
                    timeout = 4

                    # 使用更完整的浏览器请求头
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0',
                        'Accept': 'image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Referer': 'https://www.dmm.co.jp/'
                    }



                    # 使用GET请求，stream=False提高稳定性
                    response = _http_session.get(url, timeout=timeout, headers=headers, allow_redirects=True, stream=False)
                    status_code = response.status_code



                except requests.exceptions.Timeout as timeout_e:
                    current_app.logger.error(f"⏰ 请求超时: {timeout_e}")
                    raise timeout_e
                except requests.exceptions.ConnectionError as conn_e:
                    current_app.logger.error(f"🌐 连接错误: {conn_e}")
                    raise conn_e
                except requests.exceptions.RequestException as req_e:
                    current_app.logger.error(f"� 请求异常: {req_e}")
                    raise req_e
                except Exception as general_e:
                    current_app.logger.error(f"💥 未知异常: {general_e}")
                    import traceback
                    current_app.logger.error(f"💥 异常堆栈: {traceback.format_exc()}")
                    raise general_e

                # 判断链接是否有效
                is_valid = 200 <= status_code < 400

                result = {
                    "url": url,
                    "status_code": status_code,
                    "valid": is_valid
                }

                # 缓存验证结果（永久有效）
                cache_verification_result(url, status_code, is_valid, cid)

                return result
            except requests.exceptions.Timeout as e:
                current_app.logger.warning(f"⏰ 请求超时 (4秒): {url} - {str(e)}")
                return {
                    "url": url,
                    "status_code": 408,
                    "valid": False,
                    "error": f"请求超时 (4秒): {str(e)}"
                }
            except requests.exceptions.SSLError as e:
                current_app.logger.error(f"🔒 SSL错误: {url} - {str(e)}")
                return {
                    "url": url,
                    "status_code": 0,
                    "valid": False,
                    "error": f"SSL错误: {str(e)}"
                }
            except requests.exceptions.ConnectionError as e:
                current_app.logger.error(f"🌐 连接错误: {url} - {str(e)}")
                return {
                    "url": url,
                    "status_code": 0,
                    "valid": False,
                    "error": f"连接错误: {str(e)}"
                }
            except requests.exceptions.RequestException as e:
                current_app.logger.error(f"🚫 请求异常: {url} - {str(e)}")
                return {
                    "url": url,
                    "status_code": 0,
                    "valid": False,
                    "error": f"请求异常: {str(e)}"
                }
            except Exception as e:
                current_app.logger.error(f"💥 未知异常: {url} - {str(e)}")
                import traceback
                current_app.logger.error(f"💥 异常堆栈: {traceback.format_exc()}")
                return {
                    "url": url,
                    "status_code": 0,
                    "valid": False,
                    "error": f"验证失败: {str(e)}"
                }

        # 并行验证所有链接以提高速度
        import concurrent.futures

        results = []
        valid_links = []

        # 预处理链接，分离DMM和非DMM链接
        dmm_links = []
        other_links = []

        for link in links:
            url = None
            if isinstance(link, str):
                url = link
            elif isinstance(link, dict) and 'url' in link:
                url = link['url']
            else:
                results.append({
                    "url": str(link),
                    "status_code": 0,
                    "valid": False,
                    "error": "无效的链接格式"
                })
                continue

            if is_dmm_url(url):
                dmm_links.append(url)
            else:
                other_links.append(url)

        valid_links = dmm_links + other_links

        # DMM域名批量优化：如果DMM域名不可用，批量标记所有DMM链接为失败
        if dmm_links and not check_dmm_domain_availability():
            current_app.logger.warning(f"🚫 DMM域名不可用，批量跳过{len(dmm_links)}个DMM链接")
            for url in dmm_links:
                results.append({
                    "url": url,
                    "status_code": 0,
                    "valid": False,
                    "error": "DMM域名不可用"
                })
            # 只验证非DMM链接
            valid_links = other_links

        # 并行验证链接
        if valid_links:
            # 在主线程中获取应用实例
            app = current_app._get_current_object()

            # 创建一个包装函数，在Flask应用上下文中执行验证
            def verify_with_context(url):
                try:
                    with app.app_context():
                        return verify_single_link(url)
                except Exception as e:
                    # 使用app.logger而不是current_app.logger
                    with app.app_context():
                        app.logger.error(f"验证链接异常: {url} - {str(e)}")
                    return {
                        "url": url,
                        "status_code": 0,
                        "valid": False,
                        "error": f"验证异常: {str(e)}"
                    }

            # 使用线程池并行验证，最大4个并发
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                # 提交所有验证任务
                future_to_url = {executor.submit(verify_with_context, url): url for url in valid_links}

                # 收集结果，保持原始顺序
                url_results = {}
                for future in concurrent.futures.as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        result = future.result()
                        url_results[url] = result
                    except Exception as e:
                        # 使用app.logger而不是current_app.logger
                        with app.app_context():
                            app.logger.error(f"并行验证异常: {url} - {str(e)}")
                        url_results[url] = {
                            "url": url,
                            "status_code": 0,
                            "valid": False,
                            "error": f"并行验证异常: {str(e)}"
                        }

                # 按原始顺序添加结果
                for url in valid_links:
                    results.append(url_results[url])

        return jsonify({"success": True, "results": results})

    except Exception as e:
        current_app.logger.error(f"验证链接时发生错误: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"验证链接失败: {e}"}), 500

def _update_db_pic_info(conn, movie_id, target_type, save_path):
    width, height, size_kb, status = image_processor.get_image_details(save_path)
    update_query = f"UPDATE pictures SET {target_type}_path = ?, {target_type}_width = ?, {target_type}_height = ?, {target_type}_size_kb = ?, {target_type}_status = ? WHERE movie_id = ?"
    conn.execute(update_query, (save_path, width, height, size_kb, status, movie_id))
    current_app.logger.info(f"DB Updated for {target_type}: {save_path}, Status: {status}")

@api.route('/process/poster', methods=['POST'])
def process_poster_route():
    data = request.json
    movie_id, image_url, watermarks, crop = data.get('item_id'), data.get('image_url'), data.get('watermarks', []), data.get('crop', False)
    if not image_url: return jsonify({"success": False, "message": "缺少参数"}), 400
    settings = get_settings()
    
    # 处理保存路径 - 如果提供了base_path，则使用它，否则尝试从movie_id获取
    save_path = None
    if data.get('base_path'):
        save_path = f"{data.get('base_path')}-poster.jpg"
    elif movie_id:
        conn = get_db_connection()
        movie = conn.execute('SELECT item_path FROM movies WHERE id = ?', (movie_id,)).fetchone()
        if not movie: conn.close(); return jsonify({"success": False, "message": "项目不存在"}), 404
        save_path = f"{os.path.splitext(movie['item_path'])[0]}-poster.jpg"
        conn.close()
    else:
        return jsonify({"success": False, "message": "缺少保存路径信息"}), 400
    
    success, msg = image_processor.process_image_from_url(image_url, save_path, 'poster', settings, watermarks, crop_for_poster=crop)
    
    # 如果成功且有movie_id，更新数据库
    if success and movie_id:
        conn = get_db_connection()
        _update_db_pic_info(conn, movie_id, 'poster', save_path)
        conn.commit()
        conn.close()
    
    return jsonify({"success": success, "message": msg})

@api.route('/process/fanart-and-thumb', methods=['POST'])
def process_fanart_and_thumb_route():
    data = request.json
    movie_id, image_url, watermarks, crop_poster_flag = data.get('item_id'), data.get('image_url'), data.get('watermarks', []), data.get('crop_poster', False)
    if not image_url: return jsonify({"success": False, "message": "缺少参数"}), 400
    settings = get_settings()
    
    # 处理保存路径 - 如果提供了base_path，则使用它，否则尝试从movie_id获取
    base_path = data.get('base_path')
    if not base_path and movie_id:
        conn = get_db_connection()
        movie = conn.execute('SELECT item_path FROM movies WHERE id = ?', (movie_id,)).fetchone()
        if not movie: conn.close(); return jsonify({"success": False, "message": "项目不存在"}), 404
        base_path = os.path.splitext(movie['item_path'])[0]
        conn.close()
    
    if not base_path:
        return jsonify({"success": False, "message": "缺少保存路径信息"}), 400
    
    fanart_path = f"{base_path}-fanart.jpg"
    fanart_success, _ = image_processor.process_image_from_url(image_url, fanart_path, 'fanart', settings, watermarks, crop_for_poster=False)
    
    thumb_path = f"{base_path}-thumb.jpg"
    thumb_success, _ = image_processor.process_image_from_url(image_url, thumb_path, 'thumb', settings, watermarks, crop_for_poster=False)
    
    if crop_poster_flag:
        poster_path = f"{base_path}-poster.jpg"
        poster_success, _ = image_processor.process_image_from_url(image_url, poster_path, 'poster', settings, watermarks, crop_for_poster=True)
    
    # 如果有movie_id，更新数据库
    if movie_id:
        conn = get_db_connection()
        if fanart_success: _update_db_pic_info(conn, movie_id, 'fanart', fanart_path)
        if thumb_success: _update_db_pic_info(conn, movie_id, 'thumb', thumb_path)
        if crop_poster_flag and poster_success: _update_db_pic_info(conn, movie_id, 'poster', poster_path)
        conn.commit()
        conn.close()
    
    return jsonify({"success": True, "message": "图片处理完成"})

@api.route('/skip-item/<int:item_id>', methods=['POST'])
def skip_item(item_id):
    conn = get_db_connection()
    pic = conn.execute("SELECT poster_status, fanart_status, thumb_status FROM pictures WHERE movie_id = ?", (item_id,)).fetchone()
    if not pic: conn.close(); return jsonify({"success": False, "message": "未找到图片记录"}), 404
    updates = []
    if pic['poster_status'] != '高画质': updates.append("poster_status = 'NoHD'")
    if pic['fanart_status'] != '高画质': updates.append("fanart_status = 'NoHD'")
    if pic['thumb_status'] != '高画质': updates.append("thumb_status = 'NoHD'")
    if updates:
        query = f"UPDATE pictures SET {', '.join(updates)} WHERE movie_id = ?"
        conn.execute(query, (item_id,))
        conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "已标记为跳过"})

@api.route('/refresh-item-images/<int:item_id>', methods=['POST'])
def refresh_item_images(item_id):
    conn = get_db_connection()
    movie = conn.execute('SELECT item_path FROM movies WHERE id = ?', (item_id,)).fetchone()
    if not movie: conn.close(); return jsonify({"success": False, "message": "项目不存在"}), 404
    base_path = os.path.splitext(movie['item_path'])[0]
    p_w, p_h, p_s_kb, p_stat = image_processor.get_image_details(f"{base_path}-poster.jpg")
    f_w, f_h, f_s_kb, f_stat = image_processor.get_image_details(f"{base_path}-fanart.jpg")
    t_w, t_h, t_s_kb, t_stat = image_processor.get_image_details(f"{base_path}-thumb.jpg")
    conn.execute("UPDATE pictures SET poster_width=?, poster_height=?, poster_size_kb=?, poster_status=?, fanart_width=?, fanart_height=?, fanart_size_kb=?, fanart_status=?, thumb_width=?, thumb_height=?, thumb_size_kb=?, thumb_status=? WHERE movie_id = ?", (p_w, p_h, p_s_kb, p_stat, f_w, f_h, f_s_kb, f_stat, t_w, t_h, t_s_kb, t_stat, item_id))
    conn.commit()
    updated_pic = conn.execute("SELECT poster_status, fanart_status FROM pictures WHERE movie_id = ?", (item_id,)).fetchone()
    conn.close()
    return jsonify({"success": True, "message": "图片信息已刷新", "data": dict(updated_pic) if updated_pic else {}})

@api.route('/files/list', methods=['GET'])
def list_files():
    req_path = request.args.get('path', get_media_root())
    
    # 处理请求路径
    if not req_path:
        req_path = get_media_root()
    
    # 安全检查
    if not is_safe_path(req_path):
        current_app.logger.warning(f"拒绝访问路径: {req_path}, 媒体根路径: {get_media_root()}")
        return jsonify({"error": "禁止访问的路径", "details": f"请求路径: {req_path}, 媒体根路径: {get_media_root()}"}), 403
    
    # 确保路径存在
    if not os.path.exists(req_path):
        return jsonify({"error": "路径不存在", "path": req_path}), 404
    
    # 确保是目录
    if not os.path.isdir(req_path):
        return jsonify({"error": "不是有效目录", "path": req_path}), 400
    
    # 分页参数
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 200, type=int)  # 默认每页200项
    
    # 文件类型筛选
    file_types = request.args.get('file_types')
    file_type_filters = file_types.split(',') if file_types else None
    
    # 添加简单模式，只返回基本信息，不获取文件大小等详细信息
    simple_mode = request.args.get('simple', 'false').lower() == 'true'
    
    try:
        # 设置超时，避免大目录处理时间过长
        import signal
        
        def timeout_handler(signum, frame):
            _ = signum, frame  # 忽略未使用的参数
            raise TimeoutError("处理目录内容超时，目录可能包含太多文件")
        
        # 设置30秒超时
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)
        
        try:
            # 获取目录内所有项
            all_names = os.listdir(req_path)
            
            # 重置超时计时器
            signal.alarm(0)
        except TimeoutError as e:
            current_app.logger.warning(f"目录列表获取超时: {req_path}")
            return jsonify({"error": str(e)}), 504  # Gateway Timeout
        
        # 应用筛选器
        if file_type_filters:
            filtered_names = []
            for name in all_names:
                ext = os.path.splitext(name)[1].lower()
                # 如果没有扩展名但需要显示目录
                if (not ext and os.path.isdir(os.path.join(req_path, name)) and 'dir' in file_type_filters) or \
                   (ext and ext[1:] in file_type_filters):
                    filtered_names.append(name)
            all_names = filtered_names
            
        # 计算总数和分页
        total_items = len(all_names)
        total_pages = (total_items + page_size - 1) // page_size
        
        # 获取当前页的文件名
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_items)
        page_items = all_names[start_idx:end_idx]
        
        # 处理当前页的文件信息
        items = []
        
        # 在简单模式下，只获取最基本的文件信息
        if simple_mode:
            for name in page_items:
                item_abs_path = os.path.join(req_path, name)
                try:
                    is_dir = os.path.isdir(item_abs_path)
                    items.append({
                        "name": name,
                        "path": item_abs_path,
                        "is_directory": is_dir,
                        "size": 0,  # 简单模式不获取大小
                        "modified_at": 0  # 简单模式不获取修改时间
                    })
                except (FileNotFoundError, PermissionError):
                    # 跳过无权限或丢失的文件
                    continue
        else:
            # 标准模式，获取更多文件详情
            for name in page_items:
                item_abs_path = os.path.join(req_path, name)
                try:
                    stat = os.stat(item_abs_path)
                    is_dir = os.path.isdir(item_abs_path)
                    
                    # 对于目录，只获取必要信息，不递归统计大小
                    items.append({
                        "name": name,
                        "path": item_abs_path,
                        "is_directory": is_dir,
                        "size": 0 if is_dir else stat.st_size,
                        "modified_at": stat.st_mtime
                    })
                except (FileNotFoundError, PermissionError):
                    # 跳过无权限或丢失的文件
                    continue
                
        return jsonify({
            "items": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_items,
                "total_pages": total_pages
            }
        })
    except FileNotFoundError:
        return jsonify({"error": "目录未找到"}), 404
    except PermissionError:
        return jsonify({"error": "没有权限访问该目录"}), 403
    except TimeoutError as e:
        return jsonify({"error": str(e)}), 504  # Gateway Timeout
    except Exception as e:
        current_app.logger.error(f"获取文件列表失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
    finally:
        # 确保超时信号被重置
        if 'signal' in locals():
            try:
                signal.alarm(0)
            except:
                pass

@api.route('/files/rename', methods=['POST'])
def rename_file():
    old_path, new_name = request.json.get('path'), request.json.get('new_name')
    if not all([old_path, new_name]) or not is_safe_path(old_path): return jsonify({"error": "无效的请求"}), 400
    new_path = os.path.join(os.path.dirname(old_path), new_name)
    if not is_safe_path(new_path): return jsonify({"error": "无效的新路径"}), 400
    try:
        success, error = safe_rename(old_path, new_path)
        if success:
            return jsonify({"success": True, "message": "重命名成功"})
        else:
            return jsonify({"error": error}), 500
    except Exception as e: return jsonify({"error": str(e)}), 500

@api.route('/files/delete', methods=['POST'])
def delete_files():
    paths = request.json.get('paths', [])
    if not paths: return jsonify({"error": "没有提供要删除的路径"}), 400
    for path in paths:
        if not is_safe_path(path): return jsonify({"error": f"禁止删除路径: {path}"}), 403
        try:
            success, error = safe_delete(path)
            if not success:
                return jsonify({"error": error}), 500
        except Exception as e: return jsonify({"error": f"删除 {path} 失败: {e}"}), 500
    return jsonify({"success": True, "message": "删除成功"})

@api.route('/files/create-dir', methods=['POST'])
def create_directory():
    parent_path, name = request.json.get('path'), request.json.get('name')
    if not all([parent_path, name]) or not is_safe_path(parent_path): return jsonify({"error": "无效的请求"}), 400
    new_dir_path = os.path.join(parent_path, name)
    if not is_safe_path(new_dir_path): return jsonify({"error": "无效的新目录路径"}), 400
    try:
        os.makedirs(new_dir_path, exist_ok=True)
        return jsonify({"success": True, "message": "目录创建成功"})
    except Exception as e: return jsonify({"error": str(e)}), 500

@api.route('/manual/find-movie', methods=['GET'])
def find_movie_by_query():
    query = request.args.get('q', '').strip()
    if not query: return jsonify([])
    conn = get_db_connection()
    search_query = f"%{query}%"
    movies = conn.execute("SELECT id, bangou, title, item_path FROM movies WHERE bangou LIKE ? OR item_path LIKE ? LIMIT 10", (search_query, search_query)).fetchall()
    conn.close()
    return jsonify([dict(row) for row in movies])

@api.route('/manual/movie-details/<int:movie_id>', methods=['GET'])
def get_movie_details(movie_id):
    conn = get_db_connection()
    movie = conn.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)).fetchone()
    if not movie: conn.close(); return jsonify({"error": "未找到电影"}), 404
    pictures = conn.execute("SELECT * FROM pictures WHERE movie_id = ?", (movie_id,)).fetchone()
    nfo_records = conn.execute("SELECT id, nfo_path FROM nfo_data WHERE movie_id = ?", (movie_id,)).fetchall()
    conn.close()
    return jsonify({"movie": dict(movie), "pictures": dict(pictures) if pictures else {}, "nfo_files": [dict(row) for row in nfo_records]})

# 修改get_nfo_content函数
@api.route('/manual/nfo-content/<int:nfo_id>', methods=['GET'])
def get_nfo_content(nfo_id):
    """获取数据清洗模式的NFO内容"""
    conn = get_db_connection()
    nfo_record = conn.execute("SELECT nfo_path FROM nfo_data WHERE id = ?", (nfo_id,)).fetchone()
    conn.close()
    
    if not nfo_record: 
        return jsonify({"error": "未找到NFO记录"}), 404
        
    nfo_path = nfo_record['nfo_path']
    if not is_safe_path(nfo_path): 
        return jsonify({"error": "无效的NFO路径"}), 400
        
    try:
        # 解析NFO文件
        nfo_data = parse_nfo_file(nfo_path)
        
        # 确保返回的是可序列化的数据
        if nfo_data and '_nfo_path' in nfo_data:
            nfo_data.pop('_nfo_path', None)
            
        if not nfo_data:
            return jsonify({"error": "NFO文件解析失败"}), 500
            
        return jsonify(nfo_data)
    except Exception as e: 
        current_app.logger.error(f"读取NFO文件失败: {e}", exc_info=True)
        return jsonify({"error": f"读取NFO文件失败: {e}"}), 500

# 修改save_nfo_content函数
@api.route('/manual/save-nfo/<int:nfo_id>', methods=['POST'])
def save_nfo_content(nfo_id):
    """数据清洗模式保存NFO文件，同时更新数据库"""
    data = request.json
    if not data:
        return jsonify({"success": False, "message": "请求数据为空"}), 400
        
    conn = get_db_connection()
    
    try:
        # 获取NFO记录
        nfo_record = conn.execute("SELECT nfo_path, strm_name FROM nfo_data WHERE id = ?", (nfo_id,)).fetchone()
        if not nfo_record:
            conn.close()
            return jsonify({"success": False, "message": "未找到NFO记录"}), 404
            
        nfo_path = nfo_record['nfo_path']
        # 修复: sqlite3.Row对象使用索引方式访问，不要用.get()方法
        # 如果strm_name不存在，使用空字符串作为默认值
        strm_name = nfo_record['strm_name'] if 'strm_name' in nfo_record.keys() else ''
        
        if not is_safe_path(nfo_path):
            conn.close()
            return jsonify({"success": False, "message": "无效的NFO路径"}), 400
            
        # 处理标题和原始标题，从数据库角度需要拼接番号，但在NFO中已由save_nfo_file处理
        from nfo_parser import extract_bangou_from_title, save_nfo_file
        
        # 保存到NFO文件，使用'database'模式，确保适当处理番号
        success, message = save_nfo_file(nfo_path, data, mode='database')
        if not success:
            conn.close()
            return jsonify({"success": False, "message": message}), 500
            
        # 处理数据库更新
        # 为数据库中的字段处理：提取标题中的番号并清理
        _, clean_title = extract_bangou_from_title(data.get('title', ''))
        if 'title' in data:
            data['title'] = clean_title
            
        # 同样处理originaltitle
        if 'originaltitle' in data:
            _, clean_orig_title = extract_bangou_from_title(data.get('originaltitle', ''))
            data['originaltitle'] = clean_orig_title
        
        # 更新数据库中的NFO记录
        nfo_main_cols = ['originaltitle', 'plot', 'originalplot', 'tagline', 'release_date', 'year', 'rating', 'criticrating']
        nfo_main_vals = [data.get(col) for col in nfo_main_cols]
        
        # 仅更新存在的字段
        update_cols = []
        update_vals = []
        
        for i, col in enumerate(nfo_main_cols):
            if col in data:
                update_cols.append(f"{col}=?")
                update_vals.append(nfo_main_vals[i])
                
        if update_cols:
            conn.execute(f"UPDATE nfo_data SET {', '.join(update_cols)} WHERE id = ?", (*update_vals, nfo_id))
        
        # 处理相关映射（演员、类型等）
        from webhook_handler import handle_nfo_mappings
        handle_nfo_mappings(conn.cursor(), nfo_id, data)
        
        conn.commit()
        return jsonify({"success": True, "message": "NFO 已成功保存并更新数据库"})
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"保存NFO失败: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"保存失败: {e}"}), 500
    finally:
        conn.close()

# 修改get_handmade_nfo_details函数
@api.route('/handmade/nfo-details', methods=['GET'])
def get_handmade_nfo_details():
    """获取手作修正模式的NFO详情"""
    nfo_path = request.args.get('path')
    if not nfo_path or not is_safe_path(nfo_path): 
        return jsonify({"error": "无效的NFO路径"}), 400
        
    base_path = os.path.splitext(nfo_path)[0]
    poster_info = image_processor.get_image_details(f"{base_path}-poster.jpg")
    fanart_info = image_processor.get_image_details(f"{base_path}-fanart.jpg")
    thumb_info = image_processor.get_image_details(f"{base_path}-thumb.jpg")
    pictures = {
        "poster_path": f"{base_path}-poster.jpg", "poster_stats": poster_info,
        "fanart_path": f"{base_path}-fanart.jpg", "fanart_stats": fanart_info,
        "thumb_path": f"{base_path}-thumb.jpg", "thumb_stats": thumb_info,
    }
    
    # 使用修改后的NFO解析器获取数据
    nfo_data = parse_nfo_file(nfo_path)
    
    # 确保返回的是可序列化的数据
    if nfo_data and '_nfo_path' in nfo_data:
        # 不需要在JSON中传递内部字段
        nfo_data.pop('_nfo_path', None)
        
    return jsonify({"pictures": pictures, "nfo_data": nfo_data})

# 修改save_handmade_nfo函数
@api.route('/handmade/save-nfo', methods=['POST'])
def save_handmade_nfo():
    """手作修正模式保存NFO文件"""
    nfo_path = request.args.get('path')
    if not nfo_path or not is_safe_path(nfo_path):
        return jsonify({"success": False, "message": "无效的NFO路径"}), 400
    
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "message": "请求数据为空"}), 400
            
        from nfo_parser import save_nfo_file
        
        # 使用'handmade'模式，仅修改NFO文件，不更新数据库
        success, message = save_nfo_file(nfo_path, data, mode='handmade')
        
        if success:
            return jsonify({"success": True, "message": "NFO文件保存成功"})
        else:
            return jsonify({"success": False, "message": message}), 500
    except Exception as e:
        current_app.logger.error(f"保存NFO文件失败: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"保存NFO文件失败: {e}"}), 500

@api.route('/process/upload-image', methods=['POST'])
def upload_and_process_image():
    """
    处理上传的图片，添加水印并返回处理后的图片
    可以选择直接保存到特定路径
    """
    if 'image' not in request.files:
        return jsonify({"success": False, "message": "没有上传图片"}), 400
    
    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({"success": False, "message": "未选择图片"}), 400

    # 处理参数
    watermarks = request.form.getlist('watermarks[]') if 'watermarks[]' in request.form else []
    target_type = request.form.get('target_type', 'preview')  # 'preview', 'poster', 'fanart', 'thumb'
    crop_for_poster = request.form.get('crop_for_poster', 'false').lower() == 'true'
    save_path = request.form.get('save_path', '')
    
    # 保存上传的图片到临时文件
    temp_dir = tempfile.mkdtemp()
    try:
        temp_path = os.path.join(temp_dir, secure_filename(image_file.filename))
        image_file.save(temp_path)
        
        settings = get_settings()
        
        if target_type == 'preview':
            # 处理预览模式 - 返回处理后的图片，但不保存
            output_temp = os.path.join(temp_dir, f"preview_{uuid.uuid4().hex}.jpg")
            with open(temp_path, 'rb') as f:
                img = image_processor.Image.open(f).convert("RGB")
                
                if crop_for_poster:
                    crop_ratio = float(settings.get('poster_crop_ratio', 1.419))
                    target_ratio = 1 / crop_ratio
                    current_ratio = img.width / img.height
                    if current_ratio > target_ratio:
                        new_width = int(target_ratio * img.height)
                        left = img.width - new_width
                        img = img.crop((left, 0, img.width, img.height))
                
                # 只有在预览模式下，我们总是应用水印
                img = image_processor.add_watermarks(img, watermarks, settings)
                img.save(output_temp, "JPEG", quality=95)
            
            # 设置响应类型为图片
            return send_from_directory(os.path.dirname(output_temp), 
                                      os.path.basename(output_temp), 
                                      as_attachment=True,
                                      mimetype='image/jpeg')
        else:
            # 保存模式 - 处理并保存到指定路径
            if not save_path:
                return jsonify({"success": False, "message": "未指定保存路径"}), 400
                
            if not is_safe_path(save_path):
                return jsonify({"success": False, "message": "无效的保存路径"}), 403
                
            success, msg = image_processor.process_image_from_url(
                f"file://{temp_path}", save_path, target_type, settings, watermarks, crop_for_poster
            )
            
            # 如果是针对特定movie_id的，更新数据库
            movie_id = request.form.get('movie_id')
            if success and movie_id and movie_id.isdigit():
                conn = get_db_connection()
                try:
                    _update_db_pic_info(conn, int(movie_id), target_type, save_path)
                    conn.commit()
                finally:
                    conn.close()
                    
            return jsonify({"success": success, "message": msg})
    
    except Exception as e:
        current_app.logger.error(f"处理上传图片失败: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"处理失败: {e}"}), 500
    finally:
        # 清理临时文件
        shutil.rmtree(temp_dir, ignore_errors=True)

# 添加日志管理相关的路由
@api.route('/system-logs', methods=['GET'])
def get_system_logs():
    """获取系统日志文件内容"""
    try:
        log_file_path = os.path.join('logs', 'app.log')
        if not os.path.exists(log_file_path):
            return jsonify({"success": False, "message": "日志文件不存在"}), 404
            
        # 获取查询参数
        max_lines = request.args.get('max_lines', 500, type=int)
        log_level = request.args.get('level', '').upper()  # 可选的日志级别筛选
        
        # 读取日志文件
        with open(log_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 如果设置了日志级别过滤，则只返回匹配的行
        if log_level:
            lines = [line for line in lines if f' {log_level}' in line or f' {log_level}:' in line]
        
        # 返回最后的max_lines行
        logs = lines[-max_lines:] if len(lines) > max_lines else lines
        
        # 解析日志行，提取时间、级别、线程和内容
        parsed_logs = []
        for line in logs:
            try:
                # 标准日志格式通常是: 2025-07-24 12:33:05,219 INFO: 消息内容 [in /app/db_manager.py:176]
                line = line.strip()
                
                # 首先尝试分离时间戳
                timestamp_match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})\s+(.+)$', line)
                if timestamp_match:
                    timestamp = timestamp_match.group(1)
                    content = timestamp_match.group(2)
                else:
                    timestamp = ""
                    content = line
                
                # 然后尝试分离日志级别
                level_match = re.match(r'^(DEBUG|INFO|WARNING|ERROR|CRITICAL):\s+(.+)$', content)
                if level_match:
                    level = level_match.group(1)
                    content = level_match.group(2)
                else:
                    # 可能是其他格式，如"INFO 消息内容"
                    alt_level_match = re.match(r'^(DEBUG|INFO|WARNING|ERROR|CRITICAL)\s+(.+)$', content)
                    if alt_level_match:
                        level = alt_level_match.group(1)
                        content = alt_level_match.group(2)
                    else:
                        level = ""
                
                # 最后提取线程信息，通常在消息末尾 [in /path/file.py:line]
                thread_match = re.search(r'\[in\s+([^\]]+)\]$', content)
                if thread_match:
                    thread = thread_match.group(1)
                    # 从消息中移除线程信息
                    content = content.replace(f'[in {thread}]', '').strip()
                else:
                    thread = ""
                
                parsed_logs.append({
                    'timestamp': timestamp,
                    'level': level,
                    'thread': thread,
                    'message': content
                })
            except Exception as e:
                # 如果解析失败，则添加原始行
                current_app.logger.error(f"解析日志行失败: {str(e)}, 行: {line}")
                parsed_logs.append({
                    'timestamp': '',
                    'level': '',
                    'thread': '',
                    'message': line
                })
                
        return jsonify({
            "success": True, 
            "logs": parsed_logs,
            "total_lines": len(lines)
        })
    except Exception as e:
        current_app.logger.error(f"获取系统日志失败: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": f"获取系统日志失败: {str(e)}"}), 500

@api.route('/system-logs/clear', methods=['POST'])
def clear_system_logs():
    """清空系统日志文件"""
    try:
        log_file_path = os.path.join('logs', 'app.log')
        if os.path.exists(log_file_path):
            # 打开文件并截断为空
            with open(log_file_path, 'w') as f:
                f.write('')
            current_app.logger.info("系统日志已被管理员清除")
            return jsonify({"success": True, "message": "日志已清除"})
        else:
            return jsonify({"success": False, "message": "日志文件不存在"}), 404
    except Exception as e:
        current_app.logger.error(f"清除系统日志失败: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": f"清除系统日志失败: {str(e)}"}), 500

@api.route('/update-log-level', methods=['POST'])
def update_log_level():
    """更新日志级别"""
    try:
        data = request.json
        log_level = data.get('log_level', 'INFO').upper()
        
        # 验证日志级别是否有效
        if log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            return jsonify({"success": False, "message": "无效的日志级别"}), 400
        
        # 获取当前设置
        settings = get_settings()
        
        # 更新日志级别
        settings['log_level'] = log_level
        success, message, restart_needed = save_settings(settings)
        
        if success:
            # 更新当前应用的日志级别
            new_level = getattr(logging, log_level, logging.INFO)
            current_app.logger.setLevel(new_level)
            for handler in current_app.logger.handlers:
                handler.setLevel(new_level)
            
            current_app.logger.info(f"日志级别已更新为: {log_level}")
            return jsonify({"success": True, "message": f"日志级别已更新为: {log_level}"})
        else:
            return jsonify({"success": False, "message": message}), 500
    except Exception as e:
        current_app.logger.error(f"更新日志级别失败: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": f"更新日志级别失败: {str(e)}"}), 500

# 添加封面缓存管理API端点
@api.route('/cover-cache', methods=['GET'])
def get_cover_cache_status():
    """获取封面缓存状态"""
    try:
        cache_dir = get_cover_cache_dir()
        if not os.path.exists(cache_dir):
            return jsonify({"success": False, "message": "缓存目录不存在"}), 404
        
        # 获取所有缓存的封面文件
        covers = []
        total_size = 0
        for filename in os.listdir(cache_dir):
            if filename.endswith('.jpg'):
                file_path = os.path.join(cache_dir, filename)
                file_size = os.path.getsize(file_path) / 1024  # 转换为KB
                total_size += file_size
                covers.append({
                    "filename": filename,
                    "path": file_path,
                    "size_kb": round(file_size, 2),
                    "modified_at": os.path.getmtime(file_path)
                })
        
        # 按修改时间排序
        covers.sort(key=lambda x: x['modified_at'], reverse=True)
        
        settings = get_settings()
        max_covers = settings.get('latest_movies_count', 24)
        
        return jsonify({
            "success": True, 
            "cache_dir": cache_dir,
            "total_files": len(covers),
            "total_size_kb": round(total_size, 2),
            "max_covers": max_covers,
            "covers": covers
        })
    except Exception as e:
        current_app.logger.error(f"获取封面缓存状态失败: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": f"获取封面缓存状态失败: {str(e)}"}), 500

@api.route('/cover-cache/refresh', methods=['POST'])
def refresh_cover_cache():
    """刷新封面缓存"""
    try:
        settings = get_settings()
        count = settings.get('latest_movies_count', 24)
        
        # 获取最新的高画质项目
        items = _get_latest_high_quality_items(count)
        
        # 清理现有缓存
        cache_dir = get_cover_cache_dir()
        deleted_count = 0
        if os.path.isdir(cache_dir):
            for filename in os.listdir(cache_dir):
                if filename.endswith('.jpg'):
                    try:
                        os.remove(os.path.join(cache_dir, filename))
                        deleted_count += 1
                    except Exception as e:
                        current_app.logger.error(f"删除缓存文件失败: {filename}, 错误: {str(e)}")
        
        if deleted_count > 0:
            current_app.logger.info(f"已清理旧缓存: 删除了{deleted_count}个文件")
        
        # 确保缓存目录存在
        os.makedirs(cache_dir, exist_ok=True)
        
        # 创建新的缓存
        cache_count = 0
        for item in items:
            strm_name = item['strm_name']
            poster_path = item['poster_path']
            if strm_name and poster_path:
                if copy_to_cover_cache(poster_path, strm_name):
                    cache_count += 1
        
        return jsonify({
            "success": True,
            "message": f"封面缓存刷新成功，已缓存 {cache_count} 个封面",
            "cache_count": cache_count
        })
    except Exception as e:
        current_app.logger.error(f"刷新封面缓存失败: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": f"刷新封面缓存失败: {str(e)}"}), 500

@api.route('/cover-cache/clean', methods=['POST'])
def clean_cover_cache_route():
    """清理封面缓存"""
    try:
        settings = get_settings()
        max_covers = settings.get('latest_movies_count', 24)
        clean_cover_cache(max_covers)
        return jsonify({"success": True, "message": f"已清理多余的封面缓存，保留最新的 {max_covers} 个"})
    except Exception as e:
        current_app.logger.error(f"清理封面缓存失败: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": f"清理封面缓存失败: {str(e)}"}), 500

@api.route('/restart-container', methods=['POST'])
def restart_container():
    """重启容器内的服务"""
    try:
        current_app.logger.info("收到重启容器请求")
        
        # 方法1: 发送信号给supervisor主进程重启所有服务
        try:
            current_app.logger.info("尝试向supervisor发送重启信号")
            
            # 查找supervisor主进程PID
            with open("/var/run/supervisord.pid", 'r') as f:
                supervisor_pid = int(f.read().strip())
            
            # 发送SIGHUP信号重新加载配置并重启服务
            os.kill(supervisor_pid, signal.SIGHUP)
            
            current_app.logger.info(f"=== 服务重启成功 ===")
            current_app.logger.info(f"已向supervisor进程({supervisor_pid})发送SIGHUP信号")
            return jsonify({
                "success": True,
                "message": "服务正在重启，请稍后刷新页面"
            })
            
        except Exception as e:
            current_app.logger.warning(f"向supervisor发送信号失败: {e}")
        
        # 方法2: 创建重启脚本异步执行
        try:
            current_app.logger.info("尝试使用重启脚本")
            
            # 创建重启脚本，直接杀死当前进程让supervisor重启
            restart_script = """#!/bin/bash
sleep 2
# 杀死gunicorn主进程，supervisor会自动重启
pkill -f "gunicorn.*app:app" || true
# 杀死scheduler进程，supervisor会自动重启  
pkill -f "scheduler_standalone.py" || true
"""
            script_path = "/tmp/restart_services.sh"
            with open(script_path, 'w') as f:
                f.write(restart_script)
            os.chmod(script_path, 0o755)
            
            # 异步执行重启脚本
            subprocess.Popen(["/bin/bash", script_path], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
            
            return jsonify({
                "success": True,
                "message": "服务正在重启，请稍后刷新页面"
            })
            
        except Exception as e:
            current_app.logger.warning(f"重启脚本执行失败: {e}")
        
        # 方法3: 直接退出当前进程，让supervisor自动重启
        try:
            current_app.logger.info("使用进程退出方式触发重启")
            
            def delayed_exit():
                time.sleep(2)
                current_app.logger.info("执行进程退出")
                os._exit(1)  # 强制退出，supervisor会自动重启
            
            # 异步执行退出
            threading.Thread(target=delayed_exit, daemon=True).start()
            
            return jsonify({
                "success": True,
                "message": "服务正在重启，请稍后刷新页面"
            })
            
        except Exception as e:
            current_app.logger.error(f"进程退出方式失败: {e}")
        
        # 如果所有方法都失败
        return jsonify({
            "success": False,
            "message": "无法重启服务，请手动重启容器"
        }), 500
        
    except Exception as e:
        current_app.logger.error(f"重启容器失败: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"重启失败: {e}"}), 500

def _get_latest_high_quality_items(count):
    """获取最新的高画质项目
    
    Args:
        count: 要获取的项目数量
        
    Returns:
        list: 包含项目信息的字典列表
    """
    conn = get_db_connection()
    # 查询，从nfo_data表中获取strm_name
    query = """
        SELECT m.id, m.item_path, m.bangou, m.title, p.poster_path, p.poster_status, 
               COALESCE(n.strm_name, m.bangou) as strm_name
        FROM movies m 
        LEFT JOIN pictures p ON m.id = p.movie_id 
        LEFT JOIN nfo_data n ON m.id = n.movie_id
        WHERE p.poster_status = '高画质' 
        ORDER BY m.created_at DESC 
        LIMIT ?
    """
    items = conn.execute(query, (count,)).fetchall()
    conn.close()
    
    # 转换为列表字典
    return [dict(row) for row in items]

def init_app(app):
    app.register_blueprint(api, url_prefix='/api')
    @app.route('/api/media/<path:filename>')
    def serve_media_file(filename):
        # 添加调试日志
        current_app.logger.debug(f"请求访问文件: {filename}")
        
        try:
            # 特殊处理：封面缓存路径
            if filename.startswith('cover_cache/'):
                directory = 'cover_cache'
                name = filename.replace('cover_cache/', '')
                
                # 安全检查：防止路径遍历攻击
                if '..' in name or name.startswith('/'):
                    current_app.logger.warning(f"检测到可能的路径遍历尝试: {name}")
                    return "Forbidden", 403
                
                current_app.logger.debug(f"访问缓存文件: 目录={directory}, 文件名={name}")
                
                # 确保目录存在
                if not os.path.exists(directory):
                    os.makedirs(directory, exist_ok=True)
                    current_app.logger.debug(f"创建缓存目录: {directory}")
                
                # 检查文件是否存在
                full_path = os.path.join(directory, name)
                if not os.path.exists(full_path):
                    current_app.logger.warning(f"缓存文件不存在: {full_path}，请使用刷新缓存功能重新获取")
                    
                    # 返回404而不是错误消息，这样前端会显示占位图像
                    return "File not found", 404
                
                # 文件存在，发送文件
                return send_from_directory(directory, name, as_attachment=False)
            
            # 修正: 处理路径以确保正确的权限检查
            full_path = f"/{filename}"
            media_root = get_media_root()
            
            # 添加调试日志
            current_app.logger.debug(f"访问媒体文件: 完整路径={full_path}, 媒体根路径={media_root}")
            
            # 检查路径是否在允许的范围内
            if not is_safe_path(full_path):
                current_app.logger.warning(f"尝试访问禁止路径: {full_path}, 媒体根路径: {media_root}")
                return "Forbidden", 403
                
            # 确保目录和文件名正确提取
            directory = os.path.dirname(full_path)
            name = os.path.basename(full_path)
            
            # 安全检查：确保目录和文件名不含有可能导致路径遍历的内容
            if '..' in directory or '..' in name:
                current_app.logger.warning(f"检测到可能的路径遍历尝试: {directory}/{name}")
                return "Forbidden", 403
            
            # 添加调试日志
            current_app.logger.debug(f"发送文件: 目录={directory}, 文件名={name}")
            
            # 检查文件是否存在
            if not os.path.exists(os.path.join(directory, name)):
                current_app.logger.warning(f"请求的文件不存在: {directory}/{name}")
                return "File not found", 404
            
            return send_from_directory(directory, name, as_attachment=False)
            
        except Exception as e:
            current_app.logger.error(f"处理媒体文件请求时发生错误: {str(e)}", exc_info=True)
            return "Internal Server Error", 500
            
    @app.route('/api/watermarks/<path:filename>')
    def serve_watermark_file(filename):
        return send_from_directory('/app/assets', filename)

    # ==================== 性能优化与监控 API ====================

    @app.route('/api/performance/database/analyze', methods=['GET'])
    def analyze_database_performance():
        """分析数据库性能"""
        try:
            analysis = db_performance_optimizer.analyze_database_performance()
            return jsonify({
                "success": True,
                "data": analysis
            })
        except Exception as e:
            current_app.logger.error(f"数据库性能分析失败: {e}")
            return jsonify({
                "success": False,
                "message": f"分析失败: {str(e)}"
            }), 500

    @app.route('/api/performance/database/optimize', methods=['POST'])
    def optimize_database():
        """优化数据库"""
        try:
            # 创建缺失的索引
            index_result = db_performance_optimizer.create_missing_indexes()

            # 执行VACUUM
            vacuum_result = db_performance_optimizer.vacuum_database()

            return jsonify({
                "success": True,
                "data": {
                    "indexes": index_result,
                    "vacuum": vacuum_result
                }
            })
        except Exception as e:
            current_app.logger.error(f"数据库优化失败: {e}")
            return jsonify({
                "success": False,
                "message": f"优化失败: {str(e)}"
            }), 500

    @app.route('/api/performance/cache/stats', methods=['GET'])
    def get_cache_stats():
        """获取缓存统计信息"""
        try:
            stats = cache_manager.get_comprehensive_stats()
            return jsonify({
                "success": True,
                "data": stats
            })
        except Exception as e:
            current_app.logger.error(f"获取缓存统计失败: {e}")
            return jsonify({
                "success": False,
                "message": f"获取统计失败: {str(e)}"
            }), 500

    @app.route('/api/performance/cache/clear', methods=['POST'])
    def clear_cache():
        """清空缓存"""
        try:
            cache_type = request.json.get('type', 'all') if request.json else 'all'

            if cache_type == 'all':
                result = cache_manager.clear_all_caches()
            elif cache_type == 'memory':
                cache_manager.memory_cache.clear()
                result = {'memory_cache_cleared': True}
            elif cache_type == 'file':
                result = {'file_cache_deleted': cache_manager.file_cache.clear()}
            elif cache_type == 'expired':
                result = cache_manager.cleanup_all_expired()
            else:
                return jsonify({
                    "success": False,
                    "message": "无效的缓存类型"
                }), 400

            return jsonify({
                "success": True,
                "data": result
            })
        except Exception as e:
            current_app.logger.error(f"清空缓存失败: {e}")
            return jsonify({
                "success": False,
                "message": f"清空失败: {str(e)}"
            }), 500

    @app.route('/api/performance/monitoring/dashboard', methods=['GET'])
    def get_monitoring_dashboard():
        """获取监控面板数据"""
        try:
            dashboard_data = monitoring_system.get_dashboard_data()
            return jsonify({
                "success": True,
                "data": dashboard_data
            })
        except Exception as e:
            current_app.logger.error(f"获取监控数据失败: {e}")
            return jsonify({
                "success": False,
                "message": f"获取失败: {str(e)}"
            }), 500

    @app.route('/api/performance/test/comprehensive', methods=['POST'])
    def run_performance_test():
        """运行综合性能测试"""
        try:
            test_results = performance_tester.run_comprehensive_test()
            return jsonify({
                "success": True,
                "data": test_results
            })
        except Exception as e:
            current_app.logger.error(f"性能测试失败: {e}")
            return jsonify({
                "success": False,
                "message": f"测试失败: {str(e)}"
            }), 500

    @app.route('/api/performance/system/status', methods=['GET'])
    def get_system_status():
        """获取系统状态概览"""
        try:
            # 获取数据库统计
            from db_utils import db_manager
            db_status = db_manager.get_database_status()

            # 获取缓存统计
            cache_stats = cache_manager.get_comprehensive_stats()

            # 获取监控数据
            monitoring_data = monitoring_system.get_dashboard_data()

            return jsonify({
                "success": True,
                "data": {
                    "database": db_status,
                    "cache": cache_stats,
                    "monitoring": monitoring_data,
                    "timestamp": time.time()
                }
            })
        except Exception as e:
            current_app.logger.error(f"获取系统状态失败: {e}")
            return jsonify({
                "success": False,
                "message": f"获取失败: {str(e)}"
            }), 500
