# backend/db_performance.py
"""
数据库性能优化模块
包括索引管理、查询优化、性能分析等功能
"""
import logging
import time
from typing import Dict, List, Any, Optional
from db_context import db_context

logger = logging.getLogger(__name__)

class DatabasePerformanceOptimizer:
    """数据库性能优化器"""
    
    def __init__(self):
        self.logger = logger
        
        # 推荐的索引配置
        self.recommended_indexes = {
            'movies': [
                ('idx_movies_bangou', 'bangou'),
                ('idx_movies_created_at', 'created_at'),
                ('idx_movies_title', 'title'),
                ('idx_movies_path_bangou', 'item_path, bangou')  # 复合索引
            ],
            'pictures': [
                ('idx_pictures_movie_id', 'movie_id'),
                ('idx_pictures_poster_status', 'poster_status'),
                ('idx_pictures_fanart_status', 'fanart_status'),
                ('idx_pictures_thumb_status', 'thumb_status'),
                ('idx_pictures_all_status', 'poster_status, fanart_status, thumb_status')  # 复合索引
            ],
            'nfo_data': [
                ('idx_nfo_movie_id', 'movie_id'),
                ('idx_nfo_strm_name', 'strm_name'),
                ('idx_nfo_year', 'year'),
                ('idx_nfo_rating', 'rating'),
                ('idx_nfo_movie_strm', 'movie_id, strm_name'),  # 复合索引
                ('idx_nfo_year_rating', 'year, rating')  # 复合索引
            ],
            'link_verification_cache': [
                ('idx_link_cache_url', 'url'),
                ('idx_link_cache_cid', 'cid'),
                ('idx_link_cache_verified_at', 'verified_at'),
                ('idx_link_cache_status', 'status_code, is_valid')  # 复合索引
            ]
        }
    
    def analyze_database_performance(self) -> Dict[str, Any]:
        """
        分析数据库性能
        
        Returns:
            性能分析报告
        """
        report = {
            'table_stats': {},
            'index_analysis': {},
            'query_performance': {},
            'recommendations': []
        }
        
        try:
            # 分析表统计信息
            report['table_stats'] = self._analyze_table_stats()
            
            # 分析索引使用情况
            report['index_analysis'] = self._analyze_indexes()
            
            # 分析查询性能
            report['query_performance'] = self._analyze_query_performance()
            
            # 生成优化建议
            report['recommendations'] = self._generate_recommendations(report)
            
            return report
            
        except Exception as e:
            self.logger.error(f"数据库性能分析失败: {e}")
            return {'error': str(e)}
    
    def _analyze_table_stats(self) -> Dict[str, Any]:
        """分析表统计信息"""
        stats = {}
        
        tables = ['movies', 'pictures', 'nfo_data', 'link_verification_cache']
        
        for table in tables:
            try:
                # 获取表记录数
                count_result = db_context.execute_query(f"SELECT COUNT(*) FROM {table}", fetch_one=True)
                record_count = count_result[0] if count_result else 0
                
                # 获取表大小信息
                size_result = db_context.execute_query(
                    "SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()",
                    fetch_one=True
                )
                
                # 获取表的页面统计
                page_result = db_context.execute_query(f"SELECT * FROM pragma_table_info('{table}')")
                column_count = len(page_result) if page_result else 0
                
                stats[table] = {
                    'record_count': record_count,
                    'column_count': column_count,
                    'estimated_size_kb': (size_result[0] if size_result else 0) / 1024
                }
                
            except Exception as e:
                self.logger.error(f"分析表 {table} 统计信息失败: {e}")
                stats[table] = {'error': str(e)}
        
        return stats
    
    def _analyze_indexes(self) -> Dict[str, Any]:
        """分析索引使用情况"""
        index_info = {
            'existing_indexes': {},
            'missing_indexes': {},
            'unused_indexes': []
        }
        
        try:
            # 获取现有索引
            existing_indexes = db_context.execute_query(
                "SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL"
            )
            
            for index in existing_indexes or []:
                table_name = index[1]
                if table_name not in index_info['existing_indexes']:
                    index_info['existing_indexes'][table_name] = []
                
                index_info['existing_indexes'][table_name].append({
                    'name': index[0],
                    'sql': index[2]
                })
            
            # 检查缺失的推荐索引
            for table, recommended in self.recommended_indexes.items():
                existing_table_indexes = index_info['existing_indexes'].get(table, [])
                existing_names = [idx['name'] for idx in existing_table_indexes]
                
                missing = []
                for idx_name, idx_columns in recommended:
                    if idx_name not in existing_names:
                        missing.append({
                            'name': idx_name,
                            'columns': idx_columns,
                            'table': table
                        })
                
                if missing:
                    index_info['missing_indexes'][table] = missing
            
            return index_info
            
        except Exception as e:
            self.logger.error(f"分析索引失败: {e}")
            return {'error': str(e)}
    
    def _analyze_query_performance(self) -> Dict[str, Any]:
        """分析常用查询的性能"""
        performance_tests = {
            'movie_by_bangou': {
                'query': "SELECT * FROM movies WHERE bangou = ?",
                'params': ('TEST-001',),
                'description': '根据番号查找电影'
            },
            'latest_movies': {
                'query': "SELECT * FROM movies ORDER BY created_at DESC LIMIT 10",
                'params': (),
                'description': '获取最新电影'
            },
            'low_quality_pictures': {
                'query': "SELECT * FROM pictures WHERE poster_status = '低画质' OR fanart_status = '低画质'",
                'params': (),
                'description': '查找低画质图片'
            },
            'movies_with_nfo': {
                'query': "SELECT m.*, n.year, n.rating FROM movies m JOIN nfo_data n ON m.id = n.movie_id",
                'params': (),
                'description': '获取有NFO数据的电影'
            },
            'movies_by_year': {
                'query': "SELECT * FROM nfo_data WHERE year BETWEEN ? AND ? ORDER BY year DESC",
                'params': (2020, 2024),
                'description': '按年份范围查询'
            }
        }
        
        results = {}
        
        for test_name, test_config in performance_tests.items():
            try:
                # 执行查询并测量时间
                start_time = time.time()
                
                # 使用EXPLAIN QUERY PLAN分析查询计划
                explain_query = f"EXPLAIN QUERY PLAN {test_config['query']}"
                plan_result = db_context.execute_query(explain_query, test_config['params'])
                
                # 执行实际查询
                actual_result = db_context.execute_query(test_config['query'], test_config['params'])
                
                end_time = time.time()
                execution_time = end_time - start_time
                
                results[test_name] = {
                    'description': test_config['description'],
                    'execution_time_ms': round(execution_time * 1000, 2),
                    'result_count': len(actual_result) if actual_result else 0,
                    'query_plan': [dict(row) for row in plan_result] if plan_result else [],
                    'performance_rating': self._rate_performance(execution_time)
                }
                
            except Exception as e:
                results[test_name] = {
                    'description': test_config['description'],
                    'error': str(e)
                }
        
        return results
    
    def _rate_performance(self, execution_time: float) -> str:
        """评估查询性能"""
        if execution_time < 0.01:  # 10ms
            return 'excellent'
        elif execution_time < 0.05:  # 50ms
            return 'good'
        elif execution_time < 0.1:  # 100ms
            return 'fair'
        else:
            return 'poor'
    
    def _generate_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # 基于缺失索引的建议
        missing_indexes = report.get('index_analysis', {}).get('missing_indexes', {})
        for table, indexes in missing_indexes.items():
            for index in indexes:
                recommendations.append(
                    f"建议为表 {table} 创建索引: {index['name']} ({index['columns']})"
                )
        
        # 基于查询性能的建议
        query_performance = report.get('query_performance', {})
        for query_name, perf in query_performance.items():
            if perf.get('performance_rating') == 'poor':
                recommendations.append(
                    f"查询 '{perf.get('description', query_name)}' 性能较差 "
                    f"({perf.get('execution_time_ms', 0)}ms)，建议优化"
                )
        
        # 基于表大小的建议
        table_stats = report.get('table_stats', {})
        for table, stats in table_stats.items():
            if stats.get('record_count', 0) > 10000:
                recommendations.append(
                    f"表 {table} 记录数较多 ({stats['record_count']} 条)，"
                    f"建议定期清理或分区"
                )
        
        return recommendations
    
    def create_missing_indexes(self) -> Dict[str, Any]:
        """创建缺失的推荐索引"""
        results = {
            'created': [],
            'failed': [],
            'skipped': []
        }
        
        try:
            # 获取现有索引
            existing_indexes = db_context.execute_query(
                "SELECT name FROM sqlite_master WHERE type='index'"
            )
            existing_names = [idx[0] for idx in existing_indexes] if existing_indexes else []
            
            # 创建缺失的索引
            for table, indexes in self.recommended_indexes.items():
                for idx_name, idx_columns in indexes:
                    if idx_name in existing_names:
                        results['skipped'].append(f"{idx_name} (已存在)")
                        continue
                    
                    try:
                        # 创建索引
                        create_sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({idx_columns})"
                        db_context.execute_query(create_sql, fetch_all=False)
                        
                        results['created'].append(f"{idx_name} on {table}({idx_columns})")
                        self.logger.info(f"成功创建索引: {idx_name}")
                        
                    except Exception as e:
                        error_msg = f"{idx_name}: {str(e)}"
                        results['failed'].append(error_msg)
                        self.logger.error(f"创建索引失败 {idx_name}: {e}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"批量创建索引失败: {e}")
            return {'error': str(e)}
    
    def vacuum_database(self) -> Dict[str, Any]:
        """执行数据库VACUUM操作"""
        try:
            start_time = time.time()
            
            # 获取VACUUM前的数据库大小
            size_before = db_context.execute_query(
                "SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()",
                fetch_one=True
            )
            
            # 执行VACUUM
            db_context.execute_query("VACUUM", fetch_all=False)
            
            # 获取VACUUM后的数据库大小
            size_after = db_context.execute_query(
                "SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()",
                fetch_one=True
            )
            
            end_time = time.time()
            
            size_before_mb = (size_before[0] if size_before else 0) / (1024 * 1024)
            size_after_mb = (size_after[0] if size_after else 0) / (1024 * 1024)
            space_saved_mb = size_before_mb - size_after_mb
            
            return {
                'success': True,
                'execution_time_seconds': round(end_time - start_time, 2),
                'size_before_mb': round(size_before_mb, 2),
                'size_after_mb': round(size_after_mb, 2),
                'space_saved_mb': round(space_saved_mb, 2),
                'space_saved_percent': round((space_saved_mb / size_before_mb * 100) if size_before_mb > 0 else 0, 2)
            }
            
        except Exception as e:
            self.logger.error(f"VACUUM操作失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def analyze_slow_queries(self) -> Dict[str, Any]:
        """分析慢查询"""
        # 从数据库上下文获取慢查询统计
        stats = db_context.get_operation_stats()
        
        return {
            'slow_query_count': stats.get('slow_queries', 0),
            'total_queries': stats.get('total_queries', 0),
            'average_query_time_ms': round(stats.get('average_query_time', 0) * 1000, 2),
            'slow_query_threshold_ms': 1000,  # 1秒
            'recommendations': [
                "监控慢查询日志，识别需要优化的查询",
                "为频繁查询的字段添加索引",
                "考虑查询结果缓存",
                "优化复杂的JOIN查询"
            ] if stats.get('slow_queries', 0) > 0 else []
        }

# 创建全局实例
db_performance_optimizer = DatabasePerformanceOptimizer()
