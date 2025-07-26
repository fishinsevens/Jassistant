# backend/db_utils.py
"""
数据库工具模块
提供数据库管理、监控和维护功能
"""
import logging
from typing import Dict, Any, List
from db_context import db_context
from db_manager import get_connection_pool_stats, cleanup_connection_pool
from dao import movie_dao, picture_dao, nfo_dao

logger = logging.getLogger(__name__)

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.logger = logger
    
    def get_database_status(self) -> Dict[str, Any]:
        """
        获取数据库状态信息
        
        Returns:
            数据库状态字典
        """
        try:
            status = {
                'database_accessible': True,
                'tables': {},
                'operation_stats': db_context.get_operation_stats(),
                'connection_pool_stats': get_connection_pool_stats()
            }
            
            # 获取各表的记录数
            tables_info = {
                'movies': movie_dao.count(),
                'pictures': picture_dao.count(),
                'nfo_data': nfo_dao.count()
            }
            
            status['tables'] = tables_info
            status['total_records'] = sum(tables_info.values())
            
            return status
            
        except Exception as e:
            self.logger.error(f"获取数据库状态失败: {e}")
            return {
                'database_accessible': False,
                'error': str(e),
                'tables': {},
                'operation_stats': {},
                'connection_pool_stats': {}
            }
    
    def get_database_health_report(self) -> Dict[str, Any]:
        """
        获取数据库健康报告
        
        Returns:
            健康报告字典
        """
        try:
            report = {
                'overall_health': 'good',
                'issues': [],
                'recommendations': [],
                'statistics': {}
            }
            
            # 获取操作统计
            stats = db_context.get_operation_stats()
            report['statistics'] = stats
            
            # 检查慢查询
            if stats.get('slow_queries', 0) > 0:
                report['issues'].append(f"检测到 {stats['slow_queries']} 个慢查询")
                report['recommendations'].append("考虑优化慢查询或添加索引")
            
            # 检查失败查询
            if stats.get('failed_queries', 0) > 0:
                failure_rate = stats['failed_queries'] / max(stats.get('total_queries', 1), 1)
                if failure_rate > 0.01:  # 失败率超过1%
                    report['issues'].append(f"查询失败率较高: {failure_rate:.2%}")
                    report['recommendations'].append("检查数据库连接稳定性")
            
            # 检查连接池使用情况
            pool_stats = get_connection_pool_stats()
            if pool_stats.get('peak_pool_size', 0) >= pool_stats.get('current_pool_size', 0):
                report['recommendations'].append("考虑增加连接池大小以提高性能")
            
            # 获取图片统计
            picture_stats = picture_dao.get_picture_statistics()
            low_quality_count = (
                picture_stats.get('poster_low_quality', 0) +
                picture_stats.get('fanart_low_quality', 0) +
                picture_stats.get('thumb_low_quality', 0)
            )
            
            if low_quality_count > 0:
                report['issues'].append(f"发现 {low_quality_count} 个低画质图片")
                report['recommendations'].append("考虑替换低画质图片")
            
            # 根据问题数量确定整体健康状态
            if len(report['issues']) == 0:
                report['overall_health'] = 'excellent'
            elif len(report['issues']) <= 2:
                report['overall_health'] = 'good'
            elif len(report['issues']) <= 5:
                report['overall_health'] = 'fair'
            else:
                report['overall_health'] = 'poor'
            
            return report
            
        except Exception as e:
            self.logger.error(f"生成数据库健康报告失败: {e}")
            return {
                'overall_health': 'unknown',
                'error': str(e),
                'issues': ['无法生成健康报告'],
                'recommendations': ['检查数据库连接'],
                'statistics': {}
            }
    
    def optimize_database(self) -> Dict[str, Any]:
        """
        优化数据库性能
        
        Returns:
            优化结果字典
        """
        try:
            result = {
                'success': True,
                'operations_performed': [],
                'errors': []
            }
            
            # 执行VACUUM操作
            try:
                db_context.execute_query("VACUUM", fetch_all=False)
                result['operations_performed'].append("数据库VACUUM操作完成")
            except Exception as e:
                result['errors'].append(f"VACUUM操作失败: {e}")
            
            # 执行ANALYZE操作
            try:
                db_context.execute_query("ANALYZE", fetch_all=False)
                result['operations_performed'].append("数据库ANALYZE操作完成")
            except Exception as e:
                result['errors'].append(f"ANALYZE操作失败: {e}")
            
            # 执行WAL检查点
            try:
                checkpoint_result = db_context.execute_query("PRAGMA wal_checkpoint(FULL)", fetch_one=True)
                result['operations_performed'].append(f"WAL检查点操作完成: {checkpoint_result}")
            except Exception as e:
                result['errors'].append(f"WAL检查点操作失败: {e}")
            
            # 重置统计信息
            db_context.reset_stats()
            result['operations_performed'].append("重置操作统计信息")
            
            result['success'] = len(result['errors']) == 0
            return result
            
        except Exception as e:
            self.logger.error(f"数据库优化失败: {e}")
            return {
                'success': False,
                'operations_performed': [],
                'errors': [str(e)]
            }
    
    def cleanup_resources(self):
        """清理数据库资源"""
        try:
            cleanup_connection_pool()
            self.logger.info("数据库连接池已清理")
        except Exception as e:
            self.logger.error(f"清理数据库资源失败: {e}")
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        获取指定表的详细信息
        
        Args:
            table_name: 表名
            
        Returns:
            表信息字典
        """
        try:
            info = {
                'table_name': table_name,
                'exists': False,
                'columns': [],
                'indexes': [],
                'record_count': 0
            }
            
            # 检查表是否存在
            result = db_context.execute_query(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
                fetch_one=True
            )
            
            if result:
                info['exists'] = True
                
                # 获取列信息
                columns = db_context.execute_query(f"PRAGMA table_info({table_name})")
                info['columns'] = [dict(col) for col in columns] if columns else []
                
                # 获取索引信息
                indexes = db_context.execute_query(f"PRAGMA index_list({table_name})")
                info['indexes'] = [dict(idx) for idx in indexes] if indexes else []
                
                # 获取记录数
                count_result = db_context.execute_query(f"SELECT COUNT(*) FROM {table_name}", fetch_one=True)
                info['record_count'] = count_result[0] if count_result else 0
            
            return info
            
        except Exception as e:
            self.logger.error(f"获取表信息失败: {table_name}, 错误: {e}")
            return {
                'table_name': table_name,
                'exists': False,
                'error': str(e),
                'columns': [],
                'indexes': [],
                'record_count': 0
            }

# 创建全局数据库管理器实例
db_manager = DatabaseManager()
