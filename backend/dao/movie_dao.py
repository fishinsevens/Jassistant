# backend/dao/movie_dao.py
"""
电影数据访问对象
"""
from typing import List, Dict, Any, Optional
from .base_dao import BaseDAO
from db_context import db_context

class MovieDAO(BaseDAO):
    """电影数据访问对象"""
    
    def __init__(self):
        super().__init__('movies')
    
    def get_table_schema(self) -> Dict[str, str]:
        """获取movies表结构"""
        return {
            'id': 'INTEGER PRIMARY KEY',
            'item_path': 'TEXT NOT NULL UNIQUE',
            'bangou': 'TEXT',
            'title': 'TEXT',
            'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        }
    
    def find_by_path(self, item_path: str) -> Optional[Dict[str, Any]]:
        """
        根据路径查找电影
        
        Args:
            item_path: 电影路径
            
        Returns:
            电影记录或None
        """
        return self.find_one_by_condition({'item_path': item_path})
    
    def find_by_bangou(self, bangou: str) -> List[Dict[str, Any]]:
        """
        根据番号查找电影
        
        Args:
            bangou: 番号
            
        Returns:
            电影记录列表
        """
        return self.find_by_condition({'bangou': bangou})
    
    def find_latest_movies(self, limit: int = 24) -> List[Dict[str, Any]]:
        """
        获取最新添加的电影
        
        Args:
            limit: 返回数量限制
            
        Returns:
            最新电影列表
        """
        query = f"SELECT * FROM {self.table_name} ORDER BY created_at DESC LIMIT ?"
        results = db_context.execute_query(query, (limit,))
        return [dict(row) for row in results] if results else []
    
    def search_movies(self, keyword: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        搜索电影
        
        Args:
            keyword: 搜索关键词
            limit: 返回数量限制
            
        Returns:
            匹配的电影列表
        """
        query = f"""
        SELECT * FROM {self.table_name} 
        WHERE bangou LIKE ? OR title LIKE ? OR item_path LIKE ?
        ORDER BY created_at DESC LIMIT ?
        """
        search_pattern = f"%{keyword}%"
        results = db_context.execute_query(query, (search_pattern, search_pattern, search_pattern, limit))
        return [dict(row) for row in results] if results else []
    
    def get_movies_without_pictures(self) -> List[Dict[str, Any]]:
        """
        获取没有图片信息的电影
        
        Returns:
            没有图片的电影列表
        """
        query = f"""
        SELECT m.* FROM {self.table_name} m
        LEFT JOIN pictures p ON m.id = p.movie_id
        WHERE p.movie_id IS NULL
        ORDER BY m.created_at DESC
        """
        results = db_context.execute_query(query)
        return [dict(row) for row in results] if results else []
    
    def get_movies_with_low_quality_pictures(self) -> List[Dict[str, Any]]:
        """
        获取有低画质图片的电影
        
        Returns:
            有低画质图片的电影列表
        """
        query = f"""
        SELECT DISTINCT m.* FROM {self.table_name} m
        JOIN pictures p ON m.id = p.movie_id
        WHERE p.poster_status = '低画质' OR p.fanart_status = '低画质' OR p.thumb_status = '低画质'
        ORDER BY m.created_at DESC
        """
        results = db_context.execute_query(query)
        return [dict(row) for row in results] if results else []
    
    def update_bangou(self, movie_id: int, bangou: str) -> bool:
        """
        更新电影番号
        
        Args:
            movie_id: 电影ID
            bangou: 新番号
            
        Returns:
            是否更新成功
        """
        return self.update(movie_id, {'bangou': bangou})
    
    def update_title(self, movie_id: int, title: str) -> bool:
        """
        更新电影标题
        
        Args:
            movie_id: 电影ID
            title: 新标题
            
        Returns:
            是否更新成功
        """
        return self.update(movie_id, {'title': title})
    
    def batch_insert_movies(self, movies_data: List[Dict[str, Any]]) -> List[int]:
        """
        批量插入电影记录
        
        Args:
            movies_data: 电影数据列表
            
        Returns:
            插入的记录ID列表
        """
        if not movies_data:
            return []
        
        # 确保所有记录都有相同的字段
        first_record = movies_data[0]
        columns = list(first_record.keys())
        
        placeholders = ", ".join(["?" for _ in columns])
        query = f"INSERT INTO {self.table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        
        inserted_ids = []
        try:
            with db_context.get_cursor(auto_commit=False) as cursor:
                for movie_data in movies_data:
                    # 确保字段顺序一致
                    values = [movie_data.get(col) for col in columns]
                    cursor.execute(query, values)
                    inserted_ids.append(cursor.lastrowid)
                
                cursor.connection.commit()
                self.logger.info(f"成功批量插入 {len(inserted_ids)} 条电影记录")
                return inserted_ids
        except Exception as e:
            self.logger.error(f"批量插入电影记录失败: {e}")
            raise

# 创建全局实例
movie_dao = MovieDAO()
