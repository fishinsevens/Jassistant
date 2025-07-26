# backend/db_context.py
"""
数据库连接上下文管理器
提供统一的数据库连接管理，自动处理连接获取、释放和异常处理
"""
import sqlite3
import threading
import logging
import time
from contextlib import contextmanager
from typing import Optional, Generator, Dict, Any
from db_manager import get_db_connection, return_connection_to_pool, get_connection_pool_stats

logger = logging.getLogger(__name__)

class DatabaseContext:
    """数据库连接上下文管理器类"""

    def __init__(self):
        self._local = threading.local()
        self._operation_stats = {
            'total_queries': 0,
            'total_query_time': 0.0,
            'failed_queries': 0,
            'slow_queries': 0  # 查询时间超过1秒的查询
        }
        self._stats_lock = threading.Lock()
    
    @contextmanager
    def get_connection(self, auto_commit: bool = True) -> Generator[sqlite3.Connection, None, None]:
        """
        获取数据库连接的上下文管理器
        
        Args:
            auto_commit: 是否自动提交事务，默认为True
            
        Yields:
            sqlite3.Connection: 数据库连接对象
            
        Example:
            with db_context.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM movies")
                results = cursor.fetchall()
        """
        conn = None
        try:
            # 获取数据库连接
            conn = get_db_connection()
            logger.debug("数据库连接已获取")
            
            # 如果不自动提交，开始事务
            if not auto_commit:
                conn.execute("BEGIN TRANSACTION")
                logger.debug("事务已开始")
            
            yield conn
            
            # 如果不自动提交，手动提交事务
            if not auto_commit:
                conn.commit()
                logger.debug("事务已提交")
                
        except Exception as e:
            # 发生异常时回滚事务
            if conn and not auto_commit:
                try:
                    conn.rollback()
                    logger.warning("事务已回滚")
                except Exception as rollback_error:
                    logger.error(f"回滚事务失败: {rollback_error}")
            
            logger.error(f"数据库操作异常: {e}")
            raise
            
        finally:
            # 确保连接被正确释放
            if conn:
                try:
                    return_connection_to_pool(conn)
                    logger.debug("数据库连接已释放")
                except Exception as e:
                    logger.error(f"释放数据库连接失败: {e}")
    
    @contextmanager
    def get_cursor(self, auto_commit: bool = True) -> Generator[sqlite3.Cursor, None, None]:
        """
        获取数据库游标的上下文管理器
        
        Args:
            auto_commit: 是否自动提交事务，默认为True
            
        Yields:
            sqlite3.Cursor: 数据库游标对象
            
        Example:
            with db_context.get_cursor() as cursor:
                cursor.execute("SELECT * FROM movies")
                results = cursor.fetchall()
        """
        with self.get_connection(auto_commit=auto_commit) as conn:
            cursor = conn.cursor()
            try:
                yield cursor
            finally:
                cursor.close()
    
    def execute_query(self, query: str, params: tuple = (), fetch_one: bool = False,
                     fetch_all: bool = True, auto_commit: bool = True):
        """
        执行查询语句的便捷方法

        Args:
            query: SQL查询语句
            params: 查询参数
            fetch_one: 是否只获取一条记录
            fetch_all: 是否获取所有记录
            auto_commit: 是否自动提交事务

        Returns:
            查询结果或None
        """
        start_time = time.time()
        try:
            with self.get_cursor(auto_commit=auto_commit) as cursor:
                cursor.execute(query, params)

                if fetch_one:
                    result = cursor.fetchone()
                elif fetch_all:
                    result = cursor.fetchall()
                else:
                    result = cursor.rowcount

                # 更新统计信息
                query_time = time.time() - start_time
                with self._stats_lock:
                    self._operation_stats['total_queries'] += 1
                    self._operation_stats['total_query_time'] += query_time
                    if query_time > 1.0:  # 超过1秒的查询
                        self._operation_stats['slow_queries'] += 1
                        logger.warning(f"慢查询检测: {query[:100]}... 耗时: {query_time:.2f}秒")

                return result

        except Exception as e:
            with self._stats_lock:
                self._operation_stats['failed_queries'] += 1
            logger.error(f"执行查询失败: {query}, 参数: {params}, 错误: {e}")
            raise
    
    def execute_many(self, query: str, params_list: list, auto_commit: bool = True) -> int:
        """
        批量执行SQL语句
        
        Args:
            query: SQL语句
            params_list: 参数列表
            auto_commit: 是否自动提交事务
            
        Returns:
            影响的行数
        """
        try:
            with self.get_cursor(auto_commit=auto_commit) as cursor:
                cursor.executemany(query, params_list)
                return cursor.rowcount
                
        except Exception as e:
            logger.error(f"批量执行失败: {query}, 错误: {e}")
            raise

    def get_operation_stats(self) -> Dict[str, Any]:
        """
        获取数据库操作统计信息

        Returns:
            统计信息字典
        """
        with self._stats_lock:
            stats = self._operation_stats.copy()

        # 计算平均查询时间
        if stats['total_queries'] > 0:
            stats['average_query_time'] = stats['total_query_time'] / stats['total_queries']
        else:
            stats['average_query_time'] = 0.0

        # 添加连接池统计
        stats['connection_pool'] = get_connection_pool_stats()

        return stats

    def reset_stats(self):
        """重置统计信息"""
        with self._stats_lock:
            self._operation_stats = {
                'total_queries': 0,
                'total_query_time': 0.0,
                'failed_queries': 0,
                'slow_queries': 0
            }

# 创建全局数据库上下文实例
db_context = DatabaseContext()
