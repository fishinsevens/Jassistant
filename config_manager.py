# backend/config_manager.py
"""
配置管理单例
提供缓存的配置访问，减少重复的配置读取
"""
import threading
import time
import logging
from typing import Dict, Any, Optional
from config_utils import get_settings, save_settings, is_restart_required

logger = logging.getLogger(__name__)

class ConfigManager:
    """配置管理器单例"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ConfigManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._settings_cache = {}
        self._cache_timestamp = 0
        self._cache_ttl = 60  # 缓存60秒
        self._cache_lock = threading.RLock()
        self._stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'cache_refreshes': 0,
            'total_requests': 0
        }
        self._stats_lock = threading.Lock()
        self._initialized = True
        
        logger.info("配置管理器初始化完成")
    
    def get_settings(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        获取配置设置
        
        Args:
            force_refresh: 是否强制刷新缓存
            
        Returns:
            配置字典
        """
        with self._stats_lock:
            self._stats['total_requests'] += 1
        
        current_time = time.time()
        
        with self._cache_lock:
            # 检查缓存是否有效
            cache_valid = (
                not force_refresh and
                self._settings_cache and
                (current_time - self._cache_timestamp) < self._cache_ttl
            )
            
            if cache_valid:
                with self._stats_lock:
                    self._stats['cache_hits'] += 1
                logger.debug("使用缓存的配置")
                return self._settings_cache.copy()
            
            # 缓存无效或强制刷新，重新加载配置
            try:
                self._settings_cache = get_settings()
                self._cache_timestamp = current_time
                
                with self._stats_lock:
                    if force_refresh:
                        self._stats['cache_refreshes'] += 1
                    else:
                        self._stats['cache_misses'] += 1
                
                logger.debug("重新加载配置到缓存")
                return self._settings_cache.copy()
                
            except Exception as e:
                logger.error(f"加载配置失败: {e}")
                # 如果有旧缓存，返回旧缓存
                if self._settings_cache:
                    logger.warning("使用旧缓存配置")
                    return self._settings_cache.copy()
                else:
                    # 返回空配置
                    return {}
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        获取单个配置项
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        settings = self.get_settings()
        return settings.get(key, default)
    
    def update_setting(self, key: str, value: Any) -> tuple[bool, str, bool]:
        """
        更新单个配置项
        
        Args:
            key: 配置键
            value: 配置值
            
        Returns:
            (是否成功, 消息, 是否需要重启)
        """
        try:
            # 获取当前配置
            current_settings = self.get_settings()
            
            # 更新配置
            current_settings[key] = value
            
            # 保存配置
            success, message, restart_needed = save_settings(current_settings)
            
            if success:
                # 更新缓存
                with self._cache_lock:
                    self._settings_cache[key] = value
                    self._cache_timestamp = time.time()
                
                logger.info(f"配置项 {key} 已更新为: {value}")
            
            return success, message, restart_needed
            
        except Exception as e:
            error_msg = f"更新配置项失败: {e}"
            logger.error(error_msg)
            return False, error_msg, False
    
    def update_settings(self, updates: Dict[str, Any]) -> tuple[bool, str, bool]:
        """
        批量更新配置项
        
        Args:
            updates: 要更新的配置字典
            
        Returns:
            (是否成功, 消息, 是否需要重启)
        """
        try:
            # 获取当前配置
            current_settings = self.get_settings()
            
            # 批量更新配置
            current_settings.update(updates)
            
            # 保存配置
            success, message, restart_needed = save_settings(current_settings)
            
            if success:
                # 更新缓存
                with self._cache_lock:
                    self._settings_cache.update(updates)
                    self._cache_timestamp = time.time()
                
                logger.info(f"批量更新配置项: {list(updates.keys())}")
            
            return success, message, restart_needed
            
        except Exception as e:
            error_msg = f"批量更新配置失败: {e}"
            logger.error(error_msg)
            return False, error_msg, False
    
    def is_restart_required_for_key(self, key: str) -> bool:
        """
        检查指定配置项是否需要重启
        
        Args:
            key: 配置键
            
        Returns:
            是否需要重启
        """
        return is_restart_required(key)
    
    def invalidate_cache(self):
        """使缓存失效"""
        with self._cache_lock:
            self._cache_timestamp = 0
            logger.info("配置缓存已失效")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        with self._stats_lock:
            stats = self._stats.copy()
        
        # 计算命中率
        total_requests = stats['total_requests']
        if total_requests > 0:
            stats['hit_rate'] = stats['cache_hits'] / total_requests
            stats['miss_rate'] = stats['cache_misses'] / total_requests
        else:
            stats['hit_rate'] = 0.0
            stats['miss_rate'] = 0.0
        
        # 添加缓存状态
        with self._cache_lock:
            current_time = time.time()
            cache_age = current_time - self._cache_timestamp
            stats['cache_age_seconds'] = cache_age
            stats['cache_valid'] = cache_age < self._cache_ttl
            stats['cache_size'] = len(self._settings_cache)
        
        return stats
    
    def reset_stats(self):
        """重置统计信息"""
        with self._stats_lock:
            self._stats = {
                'cache_hits': 0,
                'cache_misses': 0,
                'cache_refreshes': 0,
                'total_requests': 0
            }
        logger.info("配置管理器统计信息已重置")
    
    def set_cache_ttl(self, ttl: int):
        """
        设置缓存TTL
        
        Args:
            ttl: 缓存生存时间（秒）
        """
        with self._cache_lock:
            self._cache_ttl = ttl
            logger.info(f"配置缓存TTL设置为: {ttl}秒")
    
    def get_media_root(self) -> str:
        """获取媒体根路径的便捷方法"""
        return self.get_setting('media_root', '/weiam')
    
    def get_watermark_settings(self) -> Dict[str, Any]:
        """获取水印相关设置的便捷方法"""
        settings = self.get_settings()
        return {
            'watermark_targets': settings.get('watermark_targets', ['poster', 'thumb']),
            'watermark_scale_ratio': settings.get('watermark_scale_ratio', 12),
            'watermark_horizontal_offset': settings.get('watermark_horizontal_offset', 12),
            'watermark_vertical_offset': settings.get('watermark_vertical_offset', 6),
            'watermark_spacing': settings.get('watermark_spacing', 6),
            'poster_crop_ratio': settings.get('poster_crop_ratio', 1.415)
        }
    
    def get_image_quality_settings(self) -> Dict[str, Any]:
        """获取图片质量判断设置的便捷方法"""
        settings = self.get_settings()
        return {
            'high_quality_min_height': settings.get('high_quality_min_height', 800),
            'high_quality_min_width': settings.get('high_quality_min_width', 450),
            'high_quality_min_size_kb': settings.get('high_quality_min_size_kb', 50)
        }
    
    def get_notification_settings(self) -> Dict[str, Any]:
        """获取通知相关设置的便捷方法"""
        settings = self.get_settings()
        return {
            'notification_enabled': settings.get('notification_enabled', False),
            'notification_time': settings.get('notification_time', '09:00'),
            'notification_type': settings.get('notification_type', 'custom'),
            'telegram_bot_token': settings.get('telegram_bot_token', ''),
            'telegram_chat_id': settings.get('telegram_chat_id', ''),
            'telegram_random_image_api': settings.get('telegram_random_image_api', ''),
            'notification_api_url': settings.get('notification_api_url', ''),
            'notification_route_id': settings.get('notification_route_id', '')
        }

# 创建全局配置管理器实例
config_manager = ConfigManager()

# 向后兼容的函数
def get_cached_settings():
    """向后兼容：获取缓存的配置"""
    return config_manager.get_settings()

def get_cached_setting(key: str, default: Any = None):
    """向后兼容：获取单个缓存配置项"""
    return config_manager.get_setting(key, default)
