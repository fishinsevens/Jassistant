# backend/dao/nfo_dao.py
"""
NFO数据访问对象
"""
from typing import List, Dict, Any, Optional
from .base_dao import BaseDAO
from db_context import db_context

class NfoDAO(BaseDAO):
    """NFO数据访问对象"""
    
    def __init__(self):
        super().__init__('nfo_data')
    
    def get_table_schema(self) -> Dict[str, str]:
        """获取nfo_data表结构"""
        return {
            'id': 'INTEGER PRIMARY KEY',
            'movie_id': 'INTEGER NOT NULL',
            'nfo_path': 'TEXT NOT NULL',
            'strm_name': 'TEXT NOT NULL',
            'originaltitle': 'TEXT',
            'plot': 'TEXT',
            'originalplot': 'TEXT',
            'tagline': 'TEXT',
            'release_date': 'TEXT',
            'year': 'INTEGER',
            'rating': 'REAL',
            'criticrating': 'REAL'
        }
    
    def find_by_movie_id(self, movie_id: int) -> List[Dict[str, Any]]:
        """
        根据电影ID查找NFO数据
        
        Args:
            movie_id: 电影ID
            
        Returns:
            NFO记录列表
        """
        return self.find_by_condition({'movie_id': movie_id})
    
    def find_by_strm_name(self, strm_name: str) -> List[Dict[str, Any]]:
        """
        根据STRM名称查找NFO数据
        
        Args:
            strm_name: STRM名称
            
        Returns:
            NFO记录列表
        """
        return self.find_by_condition({'strm_name': strm_name})
    
    def find_by_nfo_path(self, nfo_path: str) -> List[Dict[str, Any]]:
        """
        根据NFO路径查找数据
        
        Args:
            nfo_path: NFO文件路径
            
        Returns:
            NFO记录列表
        """
        return self.find_by_condition({'nfo_path': nfo_path})
    
    def find_by_year_range(self, start_year: int, end_year: int) -> List[Dict[str, Any]]:
        """
        根据年份范围查找NFO数据
        
        Args:
            start_year: 开始年份
            end_year: 结束年份
            
        Returns:
            NFO记录列表
        """
        query = f"SELECT * FROM {self.table_name} WHERE year BETWEEN ? AND ? ORDER BY year DESC"
        results = db_context.execute_query(query, (start_year, end_year))
        return [dict(row) for row in results] if results else []
    
    def find_by_rating_range(self, min_rating: float, max_rating: float) -> List[Dict[str, Any]]:
        """
        根据评分范围查找NFO数据
        
        Args:
            min_rating: 最低评分
            max_rating: 最高评分
            
        Returns:
            NFO记录列表
        """
        query = f"SELECT * FROM {self.table_name} WHERE rating BETWEEN ? AND ? ORDER BY rating DESC"
        results = db_context.execute_query(query, (min_rating, max_rating))
        return [dict(row) for row in results] if results else []
    
    def search_by_title(self, keyword: str) -> List[Dict[str, Any]]:
        """
        根据标题搜索NFO数据
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            匹配的NFO记录列表
        """
        query = f"""
        SELECT * FROM {self.table_name}
        WHERE originaltitle LIKE ? OR plot LIKE ? OR tagline LIKE ?
        ORDER BY year DESC
        """
        search_pattern = f"%{keyword}%"
        results = db_context.execute_query(query, (search_pattern, search_pattern, search_pattern))
        return [dict(row) for row in results] if results else []
    
    def get_nfo_with_movie_info(self, nfo_id: int) -> Optional[Dict[str, Any]]:
        """
        获取NFO数据及关联的电影信息
        
        Args:
            nfo_id: NFO记录ID
            
        Returns:
            包含电影信息的NFO记录或None
        """
        query = f"""
        SELECT n.*, m.item_path, m.bangou, m.title as movie_title, m.created_at
        FROM {self.table_name} n
        JOIN movies m ON n.movie_id = m.id
        WHERE n.id = ?
        """
        result = db_context.execute_query(query, (nfo_id,), fetch_one=True)
        return dict(result) if result else None
    
    def get_movies_with_nfo_data(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取有NFO数据的电影列表
        
        Args:
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            电影和NFO数据列表
        """
        query = f"""
        SELECT m.*, n.originaltitle, n.year, n.rating, n.release_date
        FROM movies m
        JOIN {self.table_name} n ON m.id = n.movie_id
        ORDER BY m.created_at DESC
        LIMIT ? OFFSET ?
        """
        results = db_context.execute_query(query, (limit, offset))
        return [dict(row) for row in results] if results else []
    
    def update_nfo_content(self, nfo_id: int, nfo_data: Dict[str, Any]) -> bool:
        """
        更新NFO内容
        
        Args:
            nfo_id: NFO记录ID
            nfo_data: 要更新的NFO数据
            
        Returns:
            是否更新成功
        """
        # 过滤出有效的NFO字段
        valid_fields = {
            'originaltitle', 'plot', 'originalplot', 'tagline',
            'release_date', 'year', 'rating', 'criticrating'
        }
        filtered_data = {k: v for k, v in nfo_data.items() if k in valid_fields}
        
        if not filtered_data:
            return False
        
        return self.update(nfo_id, filtered_data)
    
    def get_nfo_statistics(self) -> Dict[str, Any]:
        """
        获取NFO数据统计信息
        
        Returns:
            统计信息字典
        """
        stats = {}
        
        # 总NFO记录数
        stats['total_nfo_records'] = self.count()
        
        # 有评分的记录数
        query = f"SELECT COUNT(*) FROM {self.table_name} WHERE rating IS NOT NULL AND rating > 0"
        result = db_context.execute_query(query, fetch_one=True)
        stats['records_with_rating'] = result[0] if result else 0
        
        # 平均评分
        query = f"SELECT AVG(rating) FROM {self.table_name} WHERE rating IS NOT NULL AND rating > 0"
        result = db_context.execute_query(query, fetch_one=True)
        stats['average_rating'] = round(result[0], 2) if result and result[0] else 0
        
        # 年份分布
        query = f"""
        SELECT year, COUNT(*) as count 
        FROM {self.table_name} 
        WHERE year IS NOT NULL 
        GROUP BY year 
        ORDER BY year DESC 
        LIMIT 10
        """
        results = db_context.execute_query(query)
        stats['year_distribution'] = [dict(row) for row in results] if results else []
        
        # 评分分布
        query = f"""
        SELECT 
            CASE 
                WHEN rating >= 9 THEN '9-10'
                WHEN rating >= 8 THEN '8-9'
                WHEN rating >= 7 THEN '7-8'
                WHEN rating >= 6 THEN '6-7'
                WHEN rating >= 5 THEN '5-6'
                ELSE '0-5'
            END as rating_range,
            COUNT(*) as count
        FROM {self.table_name}
        WHERE rating IS NOT NULL AND rating > 0
        GROUP BY rating_range
        ORDER BY rating_range DESC
        """
        results = db_context.execute_query(query)
        stats['rating_distribution'] = [dict(row) for row in results] if results else []
        
        return stats
    
    def batch_insert_nfo_data(self, nfo_data_list: List[Dict[str, Any]]) -> List[int]:
        """
        批量插入NFO数据
        
        Args:
            nfo_data_list: NFO数据列表
            
        Returns:
            插入的记录ID列表
        """
        if not nfo_data_list:
            return []
        
        # 确保所有记录都有相同的字段
        first_record = nfo_data_list[0]
        columns = list(first_record.keys())
        
        placeholders = ", ".join(["?" for _ in columns])
        query = f"INSERT INTO {self.table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        
        inserted_ids = []
        try:
            with db_context.get_cursor(auto_commit=False) as cursor:
                for nfo_data in nfo_data_list:
                    # 确保字段顺序一致
                    values = [nfo_data.get(col) for col in columns]
                    cursor.execute(query, values)
                    inserted_ids.append(cursor.lastrowid)
                
                cursor.connection.commit()
                self.logger.info(f"成功批量插入 {len(inserted_ids)} 条NFO记录")
                return inserted_ids
        except Exception as e:
            self.logger.error(f"批量插入NFO记录失败: {e}")
            raise

# 创建全局实例
nfo_dao = NfoDAO()
