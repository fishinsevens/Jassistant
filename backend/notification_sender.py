# backend/notification_sender.py
import requests
import logging
from datetime import datetime, time, timedelta
from db_manager import get_db_connection
from config_utils import get_settings
import os
import json
import random
import time
import socket

logger = logging.getLogger(__name__)

# 用于跟踪上次通知发送的时间
NOTIFICATION_RECORD_FILE = os.path.join('data', 'logs', 'last_notification.json')

def _send_notification(settings, title, content):
    """
    统一的通知发送函数。
    根据设置中的通知类型选择对应的发送方式。
    """
    notification_type = settings.get('notification_type', 'custom')
    
    # 添加尝试次数记录
    max_retries = 3
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries:
        try:
            if notification_type == 'telegram':
                _send_telegram_notification(settings, title, content)
                return True  # 成功发送，直接返回
            else:  # 默认使用自定义通知
                _send_custom_notification(settings, title, content)
                return True  # 成功发送，直接返回
        except requests.exceptions.Timeout as e:
            retry_count += 1
            wait_time = retry_count * 2  # 指数退避，每次等待时间增加
            last_error = e
            logger.warning(f"通知发送超时 (尝试 {retry_count}/{max_retries}): {e}，将在 {wait_time} 秒后重试")
            time.sleep(wait_time)
        except requests.exceptions.ConnectionError as e:
            retry_count += 1
            wait_time = retry_count * 2
            last_error = e
            logger.warning(f"通知发送连接错误 (尝试 {retry_count}/{max_retries}): {e}，将在 {wait_time} 秒后重试")
            time.sleep(wait_time)
        except Exception as e:
            # 其他错误不重试
            logger.error(f"通知发送失败，未知错误: {e}")
            raise e
    
    # 如果所有重试都失败，抛出最后一个错误
    logger.error(f"通知发送失败，已重试 {max_retries} 次: {last_error}")
    raise last_error

def _send_custom_notification(settings, title, content):
    """
    发送自定义通知，通过配置的API URL和Route ID。
    """
    api_url = settings.get('notification_api_url')
    route_id = settings.get('notification_route_id')

    if not api_url or not route_id:
        logger.error("发送自定义通知失败: 未在设置中配置完整的接口地址或Route ID。")
        raise ValueError("未配置接口地址或Route ID")
    
    # 记录DNS解析结果以帮助调试
    try:
        host = api_url.split('://')[1].split(':')[0].split('/')[0]
        logger.info(f"尝试解析主机: {host}")
        ip_info = socket.gethostbyname_ex(host)
        logger.info(f"主机 {host} DNS解析结果: {ip_info}")
    except Exception as e:
        logger.warning(f"无法解析主机名: {e}")

    payload = {
        "route_id": route_id,
        "title": title,
        "content": content
    }
    
    # 增加超时时间到30秒
    logger.info(f"正在发送通知到: {api_url}")
    response = requests.post(api_url, json=payload, timeout=30)
    response.raise_for_status() # 如果请求失败 (非2xx状态码), 会抛出异常
    logger.info(f"成功发送自定义通知: {title}")

def _add_nocache_param(url):
    """
    给URL添加随机参数，防止Telegram缓存图片
    """
    # 生成一个随机数或时间戳作为参数
    random_param = f"nocache={int(time.time() * 1000)}"
    
    # 判断URL是否已有参数
    if '?' in url:
        return f"{url}&{random_param}"
    else:
        return f"{url}?{random_param}"

def _send_telegram_notification(settings, title, content):
    """
    通过Telegram机器人发送通知。
    如果配置了随机图片API URL，则发送图片消息，否则发送纯文本消息。
    """
    bot_token = settings.get('telegram_bot_token')
    chat_id = settings.get('telegram_chat_id')
    
    if not bot_token or not chat_id:
        logger.error("发送Telegram通知失败: 未在设置中配置Bot Token或Chat ID。")
        raise ValueError("未配置Telegram Bot Token或Chat ID")
    
    # 将标题和内容合并
    message_text = f"*{title}*\n\n{content}"
    
    # 获取随机图API URL
    random_image_api = settings.get('telegram_random_image_api', '')
    
    # 根据是否有随机图API URL来决定发送方式
    if random_image_api:
        # 为URL添加随机参数以防止缓存
        image_url_with_nocache = _add_nocache_param(random_image_api)
        logger.debug(f"添加防缓存参数后的图片URL: {image_url_with_nocache}")
        
        # 发送图片消息
        api_url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        payload = {
            "chat_id": chat_id,
            "photo": image_url_with_nocache,
            "caption": message_text,
            "parse_mode": "Markdown"
        }
    else:
        # 发送纯文本消息
        api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message_text,
            "parse_mode": "Markdown"
        }
    
    try:
        # 增加超时时间到30秒
        response = requests.post(api_url, json=payload, timeout=30)
        response.raise_for_status()
        logger.info(f"成功发送Telegram通知: {title}" + (" (带图片)" if random_image_api else ""))
    except Exception as e:
        # 如果发送图片失败，尝试发送纯文本消息
        if random_image_api:
            logger.warning(f"发送Telegram图片消息失败: {e}，尝试发送纯文本消息")
            try:
                api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                payload = {
                    "chat_id": chat_id,
                    "text": message_text,
                    "parse_mode": "Markdown"
                }
                response = requests.post(api_url, json=payload, timeout=30)
                response.raise_for_status()
                logger.info(f"成功发送Telegram纯文本通知: {title}")
            except Exception as e2:
                logger.error(f"发送Telegram纯文本通知失败: {e2}")
                raise e2
        else:
            logger.error(f"发送Telegram通知失败: {e}")
            raise e

def _get_last_notification_date():
    """获取上次发送每日通知的日期"""
    try:
        if not os.path.exists(os.path.dirname(NOTIFICATION_RECORD_FILE)):
            os.makedirs(os.path.dirname(NOTIFICATION_RECORD_FILE), exist_ok=True)
            
        if os.path.exists(NOTIFICATION_RECORD_FILE):
            with open(NOTIFICATION_RECORD_FILE, 'r') as f:
                data = json.load(f)
                last_date_str = data.get('last_daily_report')
                if last_date_str:
                    return datetime.strptime(last_date_str, '%Y-%m-%d').date()
    except Exception as e:
        logger.error(f"读取上次通知记录时出错: {e}")
    
    return None

def _save_notification_date(date):
    """保存本次发送通知的日期"""
    try:
        if not os.path.exists(os.path.dirname(NOTIFICATION_RECORD_FILE)):
            os.makedirs(os.path.dirname(NOTIFICATION_RECORD_FILE), exist_ok=True)
            
        data = {'last_daily_report': date.strftime('%Y-%m-%d')}
        with open(NOTIFICATION_RECORD_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"保存通知记录时出错: {e}")

def _query_with_retry(conn, query, params=(), max_retries=3):
    """执行数据库查询，带有重试机制"""
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries:
        try:
            result = conn.execute(query, params).fetchone()
            return result
        except Exception as e:
            retry_count += 1
            wait_time = retry_count * 1  # 指数退避，每次等待时间增加
            last_error = e
            logger.warning(f"数据库查询失败 (尝试 {retry_count}/{max_retries}): {e}，将在 {wait_time} 秒后重试")
            time.sleep(wait_time)
    
    # 如果所有重试都失败，抛出最后一个错误
    logger.error(f"数据库查询失败，已重试 {max_retries} 次: {last_error}")
    raise last_error

def send_daily_report():
    """查询当天的入库情况并发送每日报告"""
    logger.info("开始执行每日报告任务...")
    
    # 检查今天是否已经发送过通知
    today = datetime.today().date()
    last_notification_date = _get_last_notification_date()
    
    if last_notification_date and last_notification_date == today:
        logger.info(f"今天 ({today}) 已经发送过每日报告，跳过")
        return
    
    settings = get_settings()
    if not settings.get('notification_enabled'):
        logger.info("通知功能未启用，每日报告任务跳过。")
        return

    conn = get_db_connection()
    try:
        # 获取今天设定的通知时间
        time_parts = settings.get('notification_time', '09:00').split(':')
        hour = int(time_parts[0])
        minute = int(time_parts[1])
        
        # 计算今天和昨天的通知时间点
        today_datetime = datetime.today()
        notification_time = today_datetime.replace(hour=hour, minute=minute, second=0, microsecond=0)
        yesterday_notification_time = notification_time - timedelta(days=1)
        
        # 使用昨天通知时间到今天通知时间的范围
        logger.info(f"查询时间范围: {yesterday_notification_time} 到 {notification_time}")
        
        # 使用重试机制执行查询
        try:
            # 查询总入库数量
            total_new_row = _query_with_retry(
                conn, 
                "SELECT COUNT(id) FROM movies WHERE created_at >= ? AND created_at < ?", 
                (yesterday_notification_time, notification_time)
            )
            total_new = total_new_row[0] if total_new_row else 0
            
            # 查询低画质数量
            low_quality_new_row = _query_with_retry(
                conn,
                """
                SELECT COUNT(m.id) FROM movies m JOIN pictures p ON m.id = p.movie_id
                WHERE m.created_at >= ? AND m.created_at < ? AND 
                      (p.poster_status = '低画质' OR p.fanart_status = '低画质')
                """,
                (yesterday_notification_time, notification_time)
            )
            low_quality_new = low_quality_new_row[0] if low_quality_new_row else 0
            
        except Exception as e:
            logger.error(f"执行数据库查询失败: {e}")
            raise
        
        # 导入连接池管理函数
        from db_manager import return_connection_to_pool
        # 使用连接池管理替代直接关闭
        return_connection_to_pool(conn)

        if total_new == 0:
            logger.info("本次统计周期内无新入库影片，不发送报告。")
            return
            
        title = f"Jassistant日报 - {datetime.today().strftime('%Y-%m-%d')}"
        content = f"本次统计周期内共入库 {total_new} 部影片，其中 {low_quality_new} 部为低画质。"
        percentage = (low_quality_new / total_new) * 100 if total_new > 0 else 0
        
        if percentage < 20: content += "\n\n光影盛宴，清晰到毛孔都在跳舞喵！"
        elif percentage < 40: content += "\n\n混进几张糊图，建议佩戴滤镜～"
        elif percentage < 60: content += "\n\n提供洗眼服务，已备好眼罩和心理安慰包（摸头）"
        else: content += "\n\n警告：建议立刻撤离，保护你的眼睛！"

        try:
            result = _send_notification(settings, title, content)
            
            # 如果发送成功，保存本次通知日期
            _save_notification_date(today)
            logger.info(f"已记录今天 ({today}) 的每日报告发送状态")
        except Exception as e:
            logger.error(f"发送每日报告失败: {e}")
            # 失败不保存日期，这样下次仍会尝试发送
    except Exception as e:
        logger.error(f"查询数据库失败: {e}", exc_info=True)
        # 出现异常时尝试关闭连接
        try:
            conn.close()
        except:
            pass

def send_test_notification():
    """发送一条预设的测试通知，忽略所有条件"""
    logger.info("执行测试通知任务...")
    settings = get_settings()
    
    notification_type = settings.get('notification_type', 'custom')
    title = "这是一条来自Jassistant的测试通知"
    
    # 根据不同的通知类型准备不同的内容
    if notification_type == 'telegram':
        content = f"如果您能收到此消息，说明您的Telegram通知设置正确。\nBot Token: {settings.get('telegram_bot_token')[:6]}...\nChat ID: {settings.get('telegram_chat_id')}"
        random_image_api = settings.get('telegram_random_image_api')
        if random_image_api:
            content += f"\n\n已设置随机图片API: {random_image_api}\n您应该能看到一张随机图片。"
    else:  # 默认使用自定义通知
        content = f"如果您能收到此消息，说明您的通知设置正确。\nAPI URL: {settings.get('notification_api_url')}\nRoute ID: {settings.get('notification_route_id')}"
    
    try:
        _send_notification(settings, title, content)
        logger.info("测试通知发送成功")
        return True
    except Exception as e:
        logger.error(f"测试通知发送失败: {e}")
        raise e  # 重新抛出异常，让调用者处理
