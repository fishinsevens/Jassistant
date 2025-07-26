# backend/performance_test.py
"""
性能测试与验证模块
测试优化效果，验证性能指标
"""
import time
import statistics
import logging
from typing import Dict, List, Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 导入需要测试的模块
from db_context import db_context
from db_performance import db_performance_optimizer
from cache_manager import cache_manager
from config_manager import config_manager
from dao.movie_dao import movie_dao
from dao.picture_dao import picture_dao
from dao.nfo_dao import nfo_dao

logger = logging.getLogger(__name__)

class PerformanceTester:
    """性能测试器"""
    
    def __init__(self):
        self.results = {}
        self.logger = logger
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """运行综合性能测试"""
        self.logger.info("开始综合性能测试...")
        
        test_results = {
            'database_performance': self._test_database_performance(),
            'cache_performance': self._test_cache_performance(),
            'dao_performance': self._test_dao_performance(),
            'concurrent_performance': self._test_concurrent_performance(),
            'memory_usage': self._test_memory_usage(),
            'optimization_impact': self._test_optimization_impact()
        }
        
        # 生成性能报告
        test_results['summary'] = self._generate_performance_summary(test_results)
        
        self.logger.info("综合性能测试完成")
        return test_results
    
    def _test_database_performance(self) -> Dict[str, Any]:
        """测试数据库性能"""
        self.logger.info("测试数据库性能...")
        
        results = {
            'connection_pool_test': self._test_connection_pool(),
            'query_performance_test': self._test_query_performance(),
            'index_effectiveness_test': self._test_index_effectiveness(),
            'transaction_performance_test': self._test_transaction_performance()
        }
        
        return results
    
    def _test_connection_pool(self) -> Dict[str, Any]:
        """测试连接池性能"""
        def get_connection_time():
            start = time.time()
            with db_context.get_connection() as conn:
                conn.execute("SELECT 1")
            return time.time() - start
        
        # 测试连接获取时间
        times = []
        for _ in range(50):
            times.append(get_connection_time())
        
        return {
            'avg_connection_time_ms': round(statistics.mean(times) * 1000, 2),
            'max_connection_time_ms': round(max(times) * 1000, 2),
            'min_connection_time_ms': round(min(times) * 1000, 2),
            'std_dev_ms': round(statistics.stdev(times) * 1000, 2) if len(times) > 1 else 0,
            'test_count': len(times)
        }
    
    def _test_query_performance(self) -> Dict[str, Any]:
        """测试查询性能"""
        test_queries = {
            'simple_count': ("SELECT COUNT(*) FROM movies", ()),
            'indexed_search': ("SELECT * FROM movies WHERE bangou = ?", ("TEST-001",)),
            'join_query': ("SELECT m.*, p.poster_status FROM movies m LEFT JOIN pictures p ON m.id = p.movie_id LIMIT 10", ()),
            'complex_filter': ("SELECT * FROM nfo_data WHERE year BETWEEN ? AND ? ORDER BY rating DESC LIMIT 20", (2020, 2024)),
            'aggregation': ("SELECT year, COUNT(*), AVG(rating) FROM nfo_data WHERE year IS NOT NULL GROUP BY year", ())
        }
        
        results = {}
        
        for query_name, (query, params) in test_queries.items():
            times = []
            for _ in range(10):  # 每个查询测试10次
                start = time.time()
                try:
                    db_context.execute_query(query, params)
                    times.append(time.time() - start)
                except Exception as e:
                    self.logger.error(f"查询 {query_name} 失败: {e}")
                    times.append(float('inf'))
            
            valid_times = [t for t in times if t != float('inf')]
            if valid_times:
                results[query_name] = {
                    'avg_time_ms': round(statistics.mean(valid_times) * 1000, 2),
                    'max_time_ms': round(max(valid_times) * 1000, 2),
                    'min_time_ms': round(min(valid_times) * 1000, 2),
                    'success_rate': len(valid_times) / len(times),
                    'performance_rating': self._rate_query_performance(statistics.mean(valid_times))
                }
            else:
                results[query_name] = {'error': 'All queries failed'}
        
        return results
    
    def _rate_query_performance(self, avg_time: float) -> str:
        """评估查询性能"""
        if avg_time < 0.01:  # 10ms
            return 'excellent'
        elif avg_time < 0.05:  # 50ms
            return 'good'
        elif avg_time < 0.1:  # 100ms
            return 'fair'
        else:
            return 'poor'
    
    def _test_index_effectiveness(self) -> Dict[str, Any]:
        """测试索引有效性"""
        # 运行数据库性能分析
        analysis = db_performance_optimizer.analyze_database_performance()
        
        return {
            'existing_indexes': len(analysis.get('index_analysis', {}).get('existing_indexes', {})),
            'missing_indexes': len(analysis.get('index_analysis', {}).get('missing_indexes', {})),
            'query_performance_summary': analysis.get('query_performance', {}),
            'recommendations_count': len(analysis.get('recommendations', []))
        }
    
    def _test_transaction_performance(self) -> Dict[str, Any]:
        """测试事务性能"""
        def test_transaction():
            start = time.time()
            try:
                with db_context.get_connection(auto_commit=False) as conn:
                    cursor = conn.cursor()
                    # 模拟事务操作
                    cursor.execute("SELECT COUNT(*) FROM movies")
                    cursor.execute("SELECT COUNT(*) FROM pictures")
                    conn.commit()
                return time.time() - start
            except Exception as e:
                self.logger.error(f"事务测试失败: {e}")
                return float('inf')
        
        times = []
        for _ in range(20):
            times.append(test_transaction())
        
        valid_times = [t for t in times if t != float('inf')]
        
        if valid_times:
            return {
                'avg_transaction_time_ms': round(statistics.mean(valid_times) * 1000, 2),
                'max_transaction_time_ms': round(max(valid_times) * 1000, 2),
                'success_rate': len(valid_times) / len(times)
            }
        else:
            return {'error': 'All transactions failed'}
    
    def _test_cache_performance(self) -> Dict[str, Any]:
        """测试缓存性能"""
        self.logger.info("测试缓存性能...")
        
        results = {
            'memory_cache_test': self._test_memory_cache(),
            'file_cache_test': self._test_file_cache(),
            'query_cache_test': self._test_query_cache(),
            'cache_hit_rates': self._test_cache_hit_rates()
        }
        
        return results
    
    def _test_memory_cache(self) -> Dict[str, Any]:
        """测试内存缓存性能"""
        cache = cache_manager.memory_cache
        
        # 测试写入性能
        write_times = []
        for i in range(1000):
            start = time.time()
            cache.set(f"test_key_{i}", f"test_value_{i}")
            write_times.append(time.time() - start)
        
        # 测试读取性能
        read_times = []
        for i in range(1000):
            start = time.time()
            cache.get(f"test_key_{i}")
            read_times.append(time.time() - start)
        
        # 清理测试数据
        for i in range(1000):
            cache.delete(f"test_key_{i}")
        
        return {
            'avg_write_time_us': round(statistics.mean(write_times) * 1000000, 2),
            'avg_read_time_us': round(statistics.mean(read_times) * 1000000, 2),
            'cache_stats': cache.get_stats()
        }
    
    def _test_file_cache(self) -> Dict[str, Any]:
        """测试文件缓存性能"""
        cache = cache_manager.file_cache
        
        # 测试写入性能
        write_times = []
        test_data = "x" * 1024  # 1KB测试数据
        
        for i in range(100):
            start = time.time()
            cache.set(f"file_test_key_{i}", test_data)
            write_times.append(time.time() - start)
        
        # 测试读取性能
        read_times = []
        for i in range(100):
            start = time.time()
            cache.get(f"file_test_key_{i}")
            read_times.append(time.time() - start)
        
        # 清理测试数据
        for i in range(100):
            cache.delete(f"file_test_key_{i}")
        
        return {
            'avg_write_time_ms': round(statistics.mean(write_times) * 1000, 2),
            'avg_read_time_ms': round(statistics.mean(read_times) * 1000, 2),
            'cache_stats': cache.get_stats()
        }
    
    def _test_query_cache(self) -> Dict[str, Any]:
        """测试查询缓存性能"""
        query_cache = cache_manager.query_cache
        
        test_query = "SELECT COUNT(*) FROM movies"
        
        # 测试缓存未命中时间
        start = time.time()
        result1 = query_cache.get(test_query)
        miss_time = time.time() - start
        
        # 设置缓存
        if result1 is None:
            actual_result = db_context.execute_query(test_query)
            query_cache.set(test_query, (), actual_result)
        
        # 测试缓存命中时间
        start = time.time()
        result2 = query_cache.get(test_query)
        hit_time = time.time() - start
        
        return {
            'cache_miss_time_ms': round(miss_time * 1000, 2),
            'cache_hit_time_ms': round(hit_time * 1000, 2),
            'cache_stats': query_cache.get_stats()
        }
    
    def _test_cache_hit_rates(self) -> Dict[str, Any]:
        """测试缓存命中率"""
        return cache_manager.get_comprehensive_stats()
    
    def _test_dao_performance(self) -> Dict[str, Any]:
        """测试DAO层性能"""
        self.logger.info("测试DAO层性能...")
        
        results = {
            'movie_dao_test': self._test_movie_dao(),
            'picture_dao_test': self._test_picture_dao(),
            'nfo_dao_test': self._test_nfo_dao()
        }
        
        return results
    
    def _test_movie_dao(self) -> Dict[str, Any]:
        """测试电影DAO性能"""
        operations = {
            'count': lambda: movie_dao.count(),
            'find_all_limited': lambda: movie_dao.find_all(limit=10),
            'find_latest': lambda: movie_dao.find_latest_movies(limit=5),
            'search': lambda: movie_dao.search_movies("test", limit=10)
        }
        
        return self._benchmark_dao_operations(operations, "MovieDAO")
    
    def _test_picture_dao(self) -> Dict[str, Any]:
        """测试图片DAO性能"""
        operations = {
            'count': lambda: picture_dao.count(),
            'get_statistics': lambda: picture_dao.get_picture_statistics(),
            'find_low_quality': lambda: picture_dao.find_low_quality_pictures()
        }
        
        return self._benchmark_dao_operations(operations, "PictureDAO")
    
    def _test_nfo_dao(self) -> Dict[str, Any]:
        """测试NFO DAO性能"""
        operations = {
            'count': lambda: nfo_dao.count(),
            'get_statistics': lambda: nfo_dao.get_nfo_statistics(),
            'find_by_year_range': lambda: nfo_dao.find_by_year_range(2020, 2024)
        }
        
        return self._benchmark_dao_operations(operations, "NfoDAO")
    
    def _benchmark_dao_operations(self, operations: Dict[str, Callable], dao_name: str) -> Dict[str, Any]:
        """基准测试DAO操作"""
        results = {}
        
        for op_name, operation in operations.items():
            times = []
            errors = 0
            
            for _ in range(10):  # 每个操作测试10次
                try:
                    start = time.time()
                    operation()
                    times.append(time.time() - start)
                except Exception as e:
                    errors += 1
                    self.logger.error(f"{dao_name}.{op_name} 失败: {e}")
            
            if times:
                results[op_name] = {
                    'avg_time_ms': round(statistics.mean(times) * 1000, 2),
                    'max_time_ms': round(max(times) * 1000, 2),
                    'min_time_ms': round(min(times) * 1000, 2),
                    'success_rate': len(times) / (len(times) + errors),
                    'error_count': errors
                }
            else:
                results[op_name] = {'error': 'All operations failed', 'error_count': errors}
        
        return results
    
    def _test_concurrent_performance(self) -> Dict[str, Any]:
        """测试并发性能"""
        self.logger.info("测试并发性能...")
        
        def concurrent_database_access():
            """并发数据库访问测试"""
            try:
                start = time.time()
                movie_dao.count()
                return time.time() - start
            except Exception as e:
                self.logger.error(f"并发数据库访问失败: {e}")
                return float('inf')
        
        # 测试不同并发级别
        concurrency_levels = [1, 5, 10, 20]
        results = {}
        
        for level in concurrency_levels:
            times = []
            
            with ThreadPoolExecutor(max_workers=level) as executor:
                futures = [executor.submit(concurrent_database_access) for _ in range(level * 5)]
                
                for future in as_completed(futures):
                    result = future.result()
                    if result != float('inf'):
                        times.append(result)
            
            if times:
                results[f'concurrency_{level}'] = {
                    'avg_time_ms': round(statistics.mean(times) * 1000, 2),
                    'max_time_ms': round(max(times) * 1000, 2),
                    'throughput_ops_per_sec': round(len(times) / sum(times), 2),
                    'success_rate': len(times) / (level * 5)
                }
            else:
                results[f'concurrency_{level}'] = {'error': 'All operations failed'}
        
        return results
    
    def _test_memory_usage(self) -> Dict[str, Any]:
        """测试内存使用情况"""
        try:
            import psutil
            process = psutil.Process()
            
            return {
                'memory_usage_mb': round(process.memory_info().rss / (1024 * 1024), 2),
                'memory_percent': round(process.memory_percent(), 2),
                'cpu_percent': round(process.cpu_percent(), 2)
            }
        except ImportError:
            return {'error': 'psutil not available'}
    
    def _test_optimization_impact(self) -> Dict[str, Any]:
        """测试优化效果"""
        return {
            'database_stats': db_context.get_operation_stats(),
            'cache_stats': cache_manager.get_comprehensive_stats(),
            'config_cache_stats': config_manager.get_cache_stats()
        }
    
    def _generate_performance_summary(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """生成性能总结"""
        summary = {
            'overall_rating': 'good',
            'key_metrics': {},
            'recommendations': [],
            'test_timestamp': time.time()
        }
        
        # 提取关键指标
        db_perf = test_results.get('database_performance', {})
        if 'connection_pool_test' in db_perf:
            summary['key_metrics']['avg_connection_time_ms'] = db_perf['connection_pool_test'].get('avg_connection_time_ms', 0)
        
        cache_perf = test_results.get('cache_performance', {})
        if 'memory_cache_test' in cache_perf:
            summary['key_metrics']['memory_cache_read_time_us'] = cache_perf['memory_cache_test'].get('avg_read_time_us', 0)
        
        # 生成建议
        if summary['key_metrics'].get('avg_connection_time_ms', 0) > 10:
            summary['recommendations'].append("数据库连接时间较长，建议优化连接池配置")
        
        if summary['key_metrics'].get('memory_cache_read_time_us', 0) > 100:
            summary['recommendations'].append("内存缓存读取时间较长，建议检查缓存大小设置")
        
        return summary

# 创建全局性能测试器实例
performance_tester = PerformanceTester()
