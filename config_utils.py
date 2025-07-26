# backend/config_utils.py
import os
import yaml
import logging
from pathlib import Path

# 添加版本信息
VERSION = "1.0.4"

# 定义需要重启才能生效的设置项
RESTART_REQUIRED_SETTINGS = [
    'log_level',           # 日志级别需要重启日志系统
    'notification_enabled', # 通知开关需要重启调度器
    'notification_time',   # 通知时间需要重启调度器
    'media_root'           # 媒体根路径在多处使用，可能被缓存
]

def get_settings():
    """
    从YAML文件加载应用设置
    """
    settings_file = os.path.join('settings', 'config.yaml')
    
    # 确保settings目录存在
    os.makedirs('settings', exist_ok=True)
    
    # 默认设置
    default_settings = {
        'version': VERSION,
        
        # --- 需要重启才能生效的设置 ---
        'log_level': 'INFO',
        'notification_enabled': False,
        'notification_time': '09:00',
        'media_root': '/weiam',  # 媒体文件根路径，默认为/weiam
        
        # --- 可以动态生效的设置 ---
        # 通知设置
        'notification_type': 'custom',  # 可选值: custom, telegram
        'telegram_bot_token': '',
        'telegram_chat_id': '',
        'telegram_random_image_api': '',  # 随机图片API的URL，留空则不发送图片
        'notification_api_url': '',
        'notification_route_id': '',
        
        # 主页显示设置
        'latest_movies_count': 24,
        'cover_size': 'medium',
        'homepage_aspect_ratio': '2:3',
        'secure_mode': False,
        
        # 水印处理设置
        'watermark_targets': ['poster', 'thumb'],
        'watermark_scale_ratio': 12,
        'watermark_horizontal_offset': 12,
        'watermark_vertical_offset': 6,
        'watermark_spacing': 6,
        'poster_crop_ratio': 1.415,
        
        # 图片质量判断标准
        'high_quality_min_height': 800,  # 最小高度
        'high_quality_min_width': 450,   # 最小宽度
        'high_quality_min_size_kb': 50   # 最小文件大小（KB）
    }
    
    # 如果设置文件存在，则加载
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = yaml.safe_load(f)
            
            # 确保添加了版本号
            settings['version'] = VERSION
                
            # 如果加载的是None (空文件)，使用默认设置
            if not settings:
                settings = default_settings
            
            # 确保类型一致性
            _normalize_settings_types(settings, default_settings)
            
        except Exception as e:
            logging.error(f"读取设置文件失败: {e}")
            settings = default_settings
    else:
        # 文件不存在，使用默认设置并创建文件
        settings = default_settings
        save_settings(settings)
    
    return settings

def _normalize_settings_types(settings, default_settings):
    """
    确保设置值的类型与默认值一致
    
    Args:
        settings: 当前设置
        default_settings: 默认设置，用于参考类型
    """
    # 确保数值类型一致
    for key, default_value in default_settings.items():
        if key in settings:
            # 跳过不需要转换的值
            if key in ['watermark_targets', 'version', 'notification_time']:
                continue
                
            try:
                # 布尔值处理
                if isinstance(default_value, bool):
                    if isinstance(settings[key], str):
                        settings[key] = settings[key].lower() in ['true', 'yes', '1', 'on']
                    else:
                        settings[key] = bool(settings[key])
                # 整数处理
                elif isinstance(default_value, int):
                    settings[key] = int(settings[key])
                # 浮点数处理
                elif isinstance(default_value, float):
                    settings[key] = float(settings[key])
            except (ValueError, TypeError):
                # 如果转换失败，使用默认值
                logging.warning(f"设置项 '{key}' 的值 '{settings[key]}' 类型错误，使用默认值 '{default_value}'")
                settings[key] = default_value

def save_settings(settings, old_settings=None):
    """
    保存设置到YAML文件
    
    Args:
        settings: 新的设置
        old_settings: 旧的设置，用于比较哪些设置已更改
        
    Returns:
        (success, message, restart_needed): 
            - success: 是否保存成功
            - message: 操作消息
            - restart_needed: 是否需要重启生效
    """
    settings_file = os.path.join('settings', 'config.yaml')
    
    # 确保设置包含版本信息
    settings['version'] = VERSION
    
    # 检查是否需要重启
    restart_needed = False
    if old_settings:
        # 检查每一个需要重启的设置项是否被修改
        for key in RESTART_REQUIRED_SETTINGS:
            if key in old_settings and key in settings:
                # 转换为字符串进行比较，避免类型差异导致误判
                old_val_str = str(old_settings.get(key))
                new_val_str = str(settings.get(key))
                if old_val_str != new_val_str:
                    logging.info(f"检测到需要重启的设置已更改: {key} 从 {old_val_str} 改为 {new_val_str}")
                    restart_needed = True
                    break
    else:
        # 如果没有提供旧设置，默认不需要重启
        restart_needed = False
    
    try:
        # 确保settings目录存在
        os.makedirs('settings', exist_ok=True)
        
        with open(settings_file, 'w', encoding='utf-8') as f:
            yaml.dump(settings, f, default_flow_style=False, allow_unicode=True)
            
        msg = "设置已保存"
        if restart_needed:
            msg += "，部分设置需要重启容器才能生效"
        
        return True, msg, restart_needed
    except Exception as e:
        logging.error(f"保存设置失败: {e}")
        return False, f"保存设置失败: {e}", False
        
def is_restart_required(key):
    """
    检查指定的设置项是否需要重启才能生效
    
    Args:
        key: 设置项的键名
        
    Returns:
        bool: 是否需要重启
    """
    return key in RESTART_REQUIRED_SETTINGS

def get_restart_required_settings():
    """
    获取所有需要重启才能生效的设置项列表
    
    Returns:
        list: 设置项键名列表
    """
    return RESTART_REQUIRED_SETTINGS
