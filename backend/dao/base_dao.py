# backend/dao/base_dao.py
"""
数据库访问层基类
提供基础的CRUD操作方法
"""
import logging
from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod
from db_context import db_context

logger = logging.getLogger(__name__)

class BaseDAO(ABC):
    """数据库访问对象基类"""
    
    def __init__(self, table_name: str):
        """
        初始化DAO
        
        Args:
            table_name: 数据表名称
        """
        self.table_name = table_name
        self.logger = logger
    
    def find_by_id(self, record_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID查找记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            记录字典或None
        """
        query = f"SELECT * FROM {self.table_name} WHERE id = ?"
        result = db_context.execute_query(query, (record_id,), fetch_one=True)
        return dict(result) if result else None
    
    def find_all(self, limit: Optional[int] = None, offset: int = 0) -> List[Dict[str, Any]]:
        """
        查找所有记录
        
        Args:
            limit: 限制返回记录数
            offset: 偏移量
            
        Returns:
            记录列表
        """
        query = f"SELECT * FROM {self.table_name}"
        params = []
        
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params = [limit, offset]
        
        results = db_context.execute_query(query, tuple(params))
        return [dict(row) for row in results] if results else []
    
    def find_by_condition(self, conditions: Dict[str, Any], 
                         limit: Optional[int] = None, 
                         offset: int = 0,
                         order_by: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        根据条件查找记录
        
        Args:
            conditions: 查询条件字典
            limit: 限制返回记录数
            offset: 偏移量
            order_by: 排序字段
            
        Returns:
            记录列表
        """
        if not conditions:
            return self.find_all(limit, offset)
        
        where_clause = " AND ".join([f"{key} = ?" for key in conditions.keys()])
        query = f"SELECT * FROM {self.table_name} WHERE {where_clause}"
        
        if order_by:
            query += f" ORDER BY {order_by}"
        
        params = list(conditions.values())
        
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        
        results = db_context.execute_query(query, tuple(params))
        return [dict(row) for row in results] if results else []
    
    def find_one_by_condition(self, conditions: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        根据条件查找单条记录
        
        Args:
            conditions: 查询条件字典
            
        Returns:
            记录字典或None
        """
        results = self.find_by_condition(conditions, limit=1)
        return results[0] if results else None
    
    def count(self, conditions: Optional[Dict[str, Any]] = None) -> int:
        """
        统计记录数量
        
        Args:
            conditions: 查询条件字典
            
        Returns:
            记录数量
        """
        if conditions:
            where_clause = " AND ".join([f"{key} = ?" for key in conditions.keys()])
            query = f"SELECT COUNT(*) FROM {self.table_name} WHERE {where_clause}"
            params = tuple(conditions.values())
        else:
            query = f"SELECT COUNT(*) FROM {self.table_name}"
            params = ()
        
        result = db_context.execute_query(query, params, fetch_one=True)
        return result[0] if result else 0
    
    def insert(self, data: Dict[str, Any]) -> Optional[int]:
        """
        插入记录
        
        Args:
            data: 要插入的数据字典
            
        Returns:
            插入记录的ID或None
        """
        if not data:
            return None
        
        columns = list(data.keys())
        placeholders = ", ".join(["?" for _ in columns])
        query = f"INSERT INTO {self.table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        
        try:
            with db_context.get_cursor(auto_commit=False) as cursor:
                cursor.execute(query, tuple(data.values()))
                record_id = cursor.lastrowid
                cursor.connection.commit()
                self.logger.info(f"成功插入记录到 {self.table_name}，ID: {record_id}")
                return record_id
        except Exception as e:
            self.logger.error(f"插入记录失败: {e}")
            raise
    
    def update(self, record_id: int, data: Dict[str, Any]) -> bool:
        """
        更新记录
        
        Args:
            record_id: 记录ID
            data: 要更新的数据字典
            
        Returns:
            是否更新成功
        """
        if not data:
            return False
        
        set_clause = ", ".join([f"{key} = ?" for key in data.keys()])
        query = f"UPDATE {self.table_name} SET {set_clause} WHERE id = ?"
        params = list(data.values()) + [record_id]
        
        try:
            row_count = db_context.execute_query(query, tuple(params), 
                                               fetch_one=False, fetch_all=False)
            success = row_count > 0
            if success:
                self.logger.info(f"成功更新 {self.table_name} 记录，ID: {record_id}")
            return success
        except Exception as e:
            self.logger.error(f"更新记录失败: {e}")
            raise
    
    def delete(self, record_id: int) -> bool:
        """
        删除记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            是否删除成功
        """
        query = f"DELETE FROM {self.table_name} WHERE id = ?"
        
        try:
            row_count = db_context.execute_query(query, (record_id,), 
                                               fetch_one=False, fetch_all=False)
            success = row_count > 0
            if success:
                self.logger.info(f"成功删除 {self.table_name} 记录，ID: {record_id}")
            return success
        except Exception as e:
            self.logger.error(f"删除记录失败: {e}")
            raise
    
    def delete_by_condition(self, conditions: Dict[str, Any]) -> int:
        """
        根据条件删除记录
        
        Args:
            conditions: 删除条件字典
            
        Returns:
            删除的记录数量
        """
        if not conditions:
            raise ValueError("删除条件不能为空")
        
        where_clause = " AND ".join([f"{key} = ?" for key in conditions.keys()])
        query = f"DELETE FROM {self.table_name} WHERE {where_clause}"
        
        try:
            row_count = db_context.execute_query(query, tuple(conditions.values()), 
                                               fetch_one=False, fetch_all=False)
            self.logger.info(f"成功删除 {self.table_name} 中 {row_count} 条记录")
            return row_count
        except Exception as e:
            self.logger.error(f"批量删除记录失败: {e}")
            raise
    
    def exists(self, conditions: Dict[str, Any]) -> bool:
        """
        检查记录是否存在
        
        Args:
            conditions: 查询条件字典
            
        Returns:
            记录是否存在
        """
        return self.count(conditions) > 0
    
    @abstractmethod
    def get_table_schema(self) -> Dict[str, str]:
        """
        获取表结构定义
        子类必须实现此方法
        
        Returns:
            表结构字典，键为字段名，值为字段类型
        """
        pass
