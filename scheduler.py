# backend/scheduler.py
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_ERROR
from config_utils import get_settings
from notification_sender import send_daily_report
from db_manager import get_db_connection
import threading
from datetime import datetime

# 使用全局变量跟踪调度器实例，确保只启动一次
_scheduler_instance = None
_scheduler_lock = threading.Lock()

def database_checkpoint():
    """定期执行数据库WAL检查点，将数据写回主文件"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA wal_checkpoint(FULL)")
        result = cursor.fetchone()
        conn.close()
        logging.info(f"数据库检查点执行成功: {result}")
    except Exception as e:
        logging.error(f"数据库检查点执行失败: {e}")

def job_error_handler(event):
    """
    处理APScheduler作业错误的处理器
    
    Args:
        event: APScheduler事件对象
    """
    # 记录作业异常
    if event.exception:
        job = event.job
        job_id = job.id if job else 'unknown'
        exception = event.exception
        trace = event.traceback
        logging.error(f"调度任务 {job_id} 执行失败: {exception}")
        logging.debug(f"调度任务异常堆栈: {trace}")
    else:
        logging.error("未知调度任务错误")

def manual_send_daily_report():
    """
    手动执行每日通知任务的包装函数，带详细日志记录
    """
    try:
        logging.info(f"手动触发每日通知任务 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        send_daily_report()
        logging.info("手动触发的每日通知任务执行完成")
    except Exception as e:
        logging.error(f"手动触发的每日通知任务执行失败: {e}", exc_info=True)

def setup_scheduler(standalone=False):
    """
    初始化并返回调度器
    
    Args:
        standalone: 如果为True，添加所有定时任务；否则只初始化调度器
        
    Returns:
        BackgroundScheduler: 已配置的调度器实例
    """
    scheduler = BackgroundScheduler(daemon=True)
    
    # 添加任务执行错误监听 - 使用正确的事件常量
    scheduler.add_listener(job_error_handler, EVENT_JOB_ERROR)
    
    if standalone:
        # 独立进程模式下，添加所有定时任务
        settings = get_settings()
        if settings.get('notification_enabled'):
            try:
                time_parts = settings.get('notification_time', '09:00').split(':')
                hour = int(time_parts[0])
                minute = int(time_parts[1])
                
                # 添加每日通知任务
                scheduler.add_job(
                    send_daily_report, 
                    'cron', 
                    hour=hour, 
                    minute=minute, 
                    id='daily_report_job', 
                    replace_existing=True,
                    misfire_grace_time=3600,  # 允许的任务错过执行时间后仍然执行的时间窗口（秒）
                    max_instances=1,  # 最大同时运行实例数，防止重复执行
                    coalesce=True  # 合并错过的执行，只运行一次
                )
                
                # 添加启动后立即尝试执行一次的任务（如果今天还没发送过）
                scheduler.add_job(
                    manual_send_daily_report,
                    'date',
                    run_date=datetime.now(),
                    id='startup_daily_report_job',
                    replace_existing=True
                )
                
                logging.info(f"独立调度器: 添加了每日通知任务，将在每天 {hour:02d}:{minute:02d} 执行")
            except Exception as e:
                logging.error(f"独立调度器: 添加定时任务失败: {e}")

    # 添加数据库检查点任务（每小时执行一次）
    scheduler.add_job(
        database_checkpoint,
        'cron',
        minute=0,  # 每小时的0分执行
        id='database_checkpoint_job',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logging.info("已添加数据库检查点任务，每小时执行一次")

    return scheduler

def init_scheduler(app):
    """
    初始化并启动调度器（为兼容现有代码保留，但不再添加定时任务）
    
    Args:
        app: Flask应用实例
    """
    global _scheduler_instance
    
    # 使用锁确保线程安全
    with _scheduler_lock:
        # 如果已经初始化过调度器，则直接返回
        if _scheduler_instance is not None:
            app.logger.info("调度器已经运行，跳过重复初始化")
            return
            
        # Web进程中不再添加定时任务，这些任务将由独立进程执行
        scheduler = BackgroundScheduler(daemon=True)
        
        # 添加任务执行错误监听 - 使用正确的事件常量
        scheduler.add_listener(job_error_handler, EVENT_JOB_ERROR)
        
        # 仍然启动调度器，但不添加任务（为了与现有代码保持兼容）
        if not scheduler.running:
            scheduler.start()
            _scheduler_instance = scheduler  # 保存实例到全局变量
            app.logger.info("Web进程中的调度器已初始化，但不执行定时任务")
