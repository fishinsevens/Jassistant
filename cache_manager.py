# backend/cache_manager.py
"""
多层缓存管理系统
包括内存缓存、文件缓存和数据库查询缓存
"""
import os
import json
import pickle
import hashlib
import time
import threading
from typing import Any, Optional, Dict, List, Union
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)

class LRUCache:
    """LRU缓存实现"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache = OrderedDict()
        self.lock = threading.RLock()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self.lock:
            if key in self.cache:
                # 移动到末尾（最近使用）
                value = self.cache.pop(key)
                self.cache[key] = value
                self.stats['hits'] += 1
                return value
            else:
                self.stats['misses'] += 1
                return None
    
    def set(self, key: str, value: Any) -> None:
        """设置缓存值"""
        with self.lock:
            if key in self.cache:
                # 更新现有值
                self.cache.pop(key)
            elif len(self.cache) >= self.max_size:
                # 删除最久未使用的项
                self.cache.popitem(last=False)
                self.stats['evictions'] += 1
            
            self.cache[key] = value
    
    def delete(self, key: str) -> bool:
        """删除缓存项"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """清空缓存"""
        with self.lock:
            self.cache.clear()
    
    def size(self) -> int:
        """获取缓存大小"""
        with self.lock:
            return len(self.cache)
    
    def get_stats(self) -> Dict[str, int]:
        """获取缓存统计"""
        with self.lock:
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = (self.stats['hits'] / total_requests) if total_requests > 0 else 0
            
            return {
                **self.stats,
                'total_requests': total_requests,
                'hit_rate': round(hit_rate, 4),
                'current_size': len(self.cache),
                'max_size': self.max_size
            }

class FileCache:
    """文件缓存管理器"""
    
    def __init__(self, cache_dir: str = "/app/data/cache", max_age_seconds: int = 3600):
        self.cache_dir = cache_dir
        self.max_age_seconds = max_age_seconds
        self.lock = threading.Lock()
        
        # 确保缓存目录存在
        os.makedirs(cache_dir, exist_ok=True)
        
        self.stats = {
            'hits': 0,
            'misses': 0,
            'writes': 0,
            'deletes': 0
        }
    
    def _get_cache_path(self, key: str) -> str:
        """获取缓存文件路径"""
        # 使用MD5哈希避免文件名问题
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{key_hash}.cache")
    
    def _is_expired(self, file_path: str) -> bool:
        """检查文件是否过期"""
        try:
            file_age = time.time() - os.path.getmtime(file_path)
            return file_age > self.max_age_seconds
        except OSError:
            return True
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        cache_path = self._get_cache_path(key)
        
        with self.lock:
            try:
                if os.path.exists(cache_path) and not self._is_expired(cache_path):
                    with open(cache_path, 'rb') as f:
                        data = pickle.load(f)
                    self.stats['hits'] += 1
                    return data
                else:
                    # 文件不存在或已过期
                    if os.path.exists(cache_path):
                        os.remove(cache_path)
                    self.stats['misses'] += 1
                    return None
            except Exception as e:
                logger.error(f"读取文件缓存失败 {key}: {e}")
                self.stats['misses'] += 1
                return None
    
    def set(self, key: str, value: Any) -> bool:
        """设置缓存值"""
        cache_path = self._get_cache_path(key)
        
        with self.lock:
            try:
                with open(cache_path, 'wb') as f:
                    pickle.dump(value, f)
                self.stats['writes'] += 1
                return True
            except Exception as e:
                logger.error(f"写入文件缓存失败 {key}: {e}")
                return False
    
    def delete(self, key: str) -> bool:
        """删除缓存项"""
        cache_path = self._get_cache_path(key)
        
        with self.lock:
            try:
                if os.path.exists(cache_path):
                    os.remove(cache_path)
                    self.stats['deletes'] += 1
                    return True
                return False
            except Exception as e:
                logger.error(f"删除文件缓存失败 {key}: {e}")
                return False
    
    def clear(self) -> int:
        """清空所有缓存文件"""
        deleted_count = 0
        
        with self.lock:
            try:
                for filename in os.listdir(self.cache_dir):
                    if filename.endswith('.cache'):
                        file_path = os.path.join(self.cache_dir, filename)
                        os.remove(file_path)
                        deleted_count += 1
                        self.stats['deletes'] += 1
            except Exception as e:
                logger.error(f"清空文件缓存失败: {e}")
        
        return deleted_count
    
    def cleanup_expired(self) -> int:
        """清理过期的缓存文件"""
        deleted_count = 0
        
        with self.lock:
            try:
                for filename in os.listdir(self.cache_dir):
                    if filename.endswith('.cache'):
                        file_path = os.path.join(self.cache_dir, filename)
                        if self._is_expired(file_path):
                            os.remove(file_path)
                            deleted_count += 1
                            self.stats['deletes'] += 1
            except Exception as e:
                logger.error(f"清理过期缓存失败: {e}")
        
        return deleted_count
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self.lock:
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = (self.stats['hits'] / total_requests) if total_requests > 0 else 0
            
            # 计算缓存目录大小
            cache_size = 0
            file_count = 0
            try:
                for filename in os.listdir(self.cache_dir):
                    if filename.endswith('.cache'):
                        file_path = os.path.join(self.cache_dir, filename)
                        cache_size += os.path.getsize(file_path)
                        file_count += 1
            except Exception:
                pass
            
            return {
                **self.stats,
                'total_requests': total_requests,
                'hit_rate': round(hit_rate, 4),
                'file_count': file_count,
                'cache_size_mb': round(cache_size / (1024 * 1024), 2),
                'max_age_seconds': self.max_age_seconds
            }

class QueryCache:
    """数据库查询缓存"""
    
    def __init__(self, memory_cache: LRUCache, file_cache: FileCache):
        self.memory_cache = memory_cache
        self.file_cache = file_cache
        self.stats = {
            'memory_hits': 0,
            'file_hits': 0,
            'misses': 0,
            'stores': 0
        }
        self.lock = threading.Lock()
    
    def _generate_cache_key(self, query: str, params: tuple = ()) -> str:
        """生成查询缓存键"""
        # 组合查询和参数生成唯一键
        cache_data = f"{query}:{str(params)}"
        return f"query:{hashlib.md5(cache_data.encode()).hexdigest()}"
    
    def get(self, query: str, params: tuple = ()) -> Optional[Any]:
        """获取查询缓存"""
        cache_key = self._generate_cache_key(query, params)
        
        with self.lock:
            # 首先尝试内存缓存
            result = self.memory_cache.get(cache_key)
            if result is not None:
                self.stats['memory_hits'] += 1
                return result
            
            # 然后尝试文件缓存
            result = self.file_cache.get(cache_key)
            if result is not None:
                # 将结果放入内存缓存
                self.memory_cache.set(cache_key, result)
                self.stats['file_hits'] += 1
                return result
            
            self.stats['misses'] += 1
            return None
    
    def set(self, query: str, params: tuple, result: Any) -> None:
        """设置查询缓存"""
        cache_key = self._generate_cache_key(query, params)
        
        with self.lock:
            # 同时存储到内存和文件缓存
            self.memory_cache.set(cache_key, result)
            self.file_cache.set(cache_key, result)
            self.stats['stores'] += 1
    
    def invalidate_pattern(self, table_name: str) -> int:
        """根据表名模式失效相关缓存"""
        # 这是一个简化实现，实际应用中可能需要更复杂的失效策略
        invalidated_count = 0
        
        with self.lock:
            # 清空所有缓存（简化实现）
            self.memory_cache.clear()
            invalidated_count += self.file_cache.clear()
            
            logger.info(f"因表 {table_name} 更新而失效 {invalidated_count} 个查询缓存")
        
        return invalidated_count
    
    def get_stats(self) -> Dict[str, Any]:
        """获取查询缓存统计"""
        with self.lock:
            total_requests = (self.stats['memory_hits'] + 
                            self.stats['file_hits'] + 
                            self.stats['misses'])
            
            hit_rate = ((self.stats['memory_hits'] + self.stats['file_hits']) / 
                       total_requests) if total_requests > 0 else 0
            
            return {
                **self.stats,
                'total_requests': total_requests,
                'hit_rate': round(hit_rate, 4),
                'memory_cache_stats': self.memory_cache.get_stats(),
                'file_cache_stats': self.file_cache.get_stats()
            }

class CacheManager:
    """统一缓存管理器"""
    
    def __init__(self, 
                 memory_cache_size: int = 1000,
                 file_cache_dir: str = "/app/data/cache",
                 file_cache_max_age: int = 3600):
        
        # 初始化各层缓存
        self.memory_cache = LRUCache(memory_cache_size)
        self.file_cache = FileCache(file_cache_dir, file_cache_max_age)
        self.query_cache = QueryCache(self.memory_cache, self.file_cache)
        
        # 特定用途的缓存
        self.image_cache = FileCache(
            os.path.join(file_cache_dir, "images"), 
            max_age_seconds=24*3600  # 图片缓存24小时
        )
        
        self.config_cache = LRUCache(100)  # 配置缓存
        
        logger.info("缓存管理器初始化完成")
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """获取综合缓存统计"""
        return {
            'memory_cache': self.memory_cache.get_stats(),
            'file_cache': self.file_cache.get_stats(),
            'query_cache': self.query_cache.get_stats(),
            'image_cache': self.image_cache.get_stats(),
            'config_cache': self.config_cache.get_stats()
        }
    
    def cleanup_all_expired(self) -> Dict[str, int]:
        """清理所有过期缓存"""
        return {
            'file_cache_deleted': self.file_cache.cleanup_expired(),
            'image_cache_deleted': self.image_cache.cleanup_expired()
        }
    
    def clear_all_caches(self) -> Dict[str, int]:
        """清空所有缓存"""
        return {
            'memory_cache_cleared': self.memory_cache.size(),
            'file_cache_deleted': self.file_cache.clear(),
            'image_cache_deleted': self.image_cache.clear(),
            'config_cache_cleared': self.config_cache.size()
        }

# 创建全局缓存管理器实例
cache_manager = CacheManager()
