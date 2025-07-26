# backend/dao/picture_dao.py
"""
图片数据访问对象
"""
from typing import List, Dict, Any, Optional
from .base_dao import BaseDAO
from db_context import db_context

class PictureDAO(BaseDAO):
    """图片数据访问对象"""
    
    def __init__(self):
        super().__init__('pictures')
    
    def get_table_schema(self) -> Dict[str, str]:
        """获取pictures表结构"""
        return {
            'id': 'INTEGER PRIMARY KEY',
            'movie_id': 'INTEGER NOT NULL UNIQUE',
            'poster_path': 'TEXT',
            'poster_width': 'INTEGER',
            'poster_height': 'INTEGER',
            'poster_size_kb': 'REAL',
            'poster_status': 'TEXT',
            'fanart_path': 'TEXT',
            'fanart_width': 'INTEGER',
            'fanart_height': 'INTEGER',
            'fanart_size_kb': 'REAL',
            'fanart_status': 'TEXT',
            'thumb_path': 'TEXT',
            'thumb_width': 'INTEGER',
            'thumb_height': 'INTEGER',
            'thumb_size_kb': 'REAL',
            'thumb_status': 'TEXT'
        }
    
    def find_by_movie_id(self, movie_id: int) -> Optional[Dict[str, Any]]:
        """
        根据电影ID查找图片信息
        
        Args:
            movie_id: 电影ID
            
        Returns:
            图片记录或None
        """
        return self.find_one_by_condition({'movie_id': movie_id})
    
    def find_low_quality_pictures(self, picture_type: str = None) -> List[Dict[str, Any]]:
        """
        查找低画质图片
        
        Args:
            picture_type: 图片类型 ('poster', 'fanart', 'thumb')，None表示所有类型
            
        Returns:
            低画质图片列表
        """
        if picture_type:
            conditions = {f'{picture_type}_status': '低画质'}
            return self.find_by_condition(conditions)
        else:
            # 查找任何类型的低画质图片
            query = f"""
            SELECT * FROM {self.table_name}
            WHERE poster_status = '低画质' OR fanart_status = '低画质' OR thumb_status = '低画质'
            """
            results = db_context.execute_query(query)
            return [dict(row) for row in results] if results else []
    
    def find_missing_pictures(self, picture_type: str = None) -> List[Dict[str, Any]]:
        """
        查找缺失图片的记录
        
        Args:
            picture_type: 图片类型 ('poster', 'fanart', 'thumb')，None表示所有类型
            
        Returns:
            缺失图片的记录列表
        """
        if picture_type:
            query = f"""
            SELECT * FROM {self.table_name}
            WHERE {picture_type}_path IS NULL OR {picture_type}_path = ''
            """
        else:
            query = f"""
            SELECT * FROM {self.table_name}
            WHERE (poster_path IS NULL OR poster_path = '') 
               OR (fanart_path IS NULL OR fanart_path = '')
               OR (thumb_path IS NULL OR thumb_path = '')
            """
        
        results = db_context.execute_query(query)
        return [dict(row) for row in results] if results else []
    
    def update_poster_info(self, movie_id: int, poster_data: Dict[str, Any]) -> bool:
        """
        更新海报信息
        
        Args:
            movie_id: 电影ID
            poster_data: 海报数据字典
            
        Returns:
            是否更新成功
        """
        # 过滤出海报相关字段
        poster_fields = {k: v for k, v in poster_data.items() 
                        if k.startswith('poster_')}
        
        if not poster_fields:
            return False
        
        # 查找现有记录
        existing = self.find_by_movie_id(movie_id)
        if existing:
            return self.update(existing['id'], poster_fields)
        else:
            # 创建新记录
            new_data = {'movie_id': movie_id, **poster_fields}
            return self.insert(new_data) is not None
    
    def update_fanart_info(self, movie_id: int, fanart_data: Dict[str, Any]) -> bool:
        """
        更新背景图信息
        
        Args:
            movie_id: 电影ID
            fanart_data: 背景图数据字典
            
        Returns:
            是否更新成功
        """
        # 过滤出背景图相关字段
        fanart_fields = {k: v for k, v in fanart_data.items() 
                        if k.startswith('fanart_')}
        
        if not fanart_fields:
            return False
        
        # 查找现有记录
        existing = self.find_by_movie_id(movie_id)
        if existing:
            return self.update(existing['id'], fanart_fields)
        else:
            # 创建新记录
            new_data = {'movie_id': movie_id, **fanart_fields}
            return self.insert(new_data) is not None
    
    def update_thumb_info(self, movie_id: int, thumb_data: Dict[str, Any]) -> bool:
        """
        更新缩略图信息
        
        Args:
            movie_id: 电影ID
            thumb_data: 缩略图数据字典
            
        Returns:
            是否更新成功
        """
        # 过滤出缩略图相关字段
        thumb_fields = {k: v for k, v in thumb_data.items() 
                       if k.startswith('thumb_')}
        
        if not thumb_fields:
            return False
        
        # 查找现有记录
        existing = self.find_by_movie_id(movie_id)
        if existing:
            return self.update(existing['id'], thumb_fields)
        else:
            # 创建新记录
            new_data = {'movie_id': movie_id, **thumb_fields}
            return self.insert(new_data) is not None
    
    def get_picture_statistics(self) -> Dict[str, int]:
        """
        获取图片统计信息
        
        Returns:
            统计信息字典
        """
        stats = {}
        
        # 总图片记录数
        stats['total_records'] = self.count()
        
        # 各类型图片的统计
        for pic_type in ['poster', 'fanart', 'thumb']:
            # 有图片的数量
            query = f"SELECT COUNT(*) FROM {self.table_name} WHERE {pic_type}_path IS NOT NULL AND {pic_type}_path != ''"
            result = db_context.execute_query(query, fetch_one=True)
            stats[f'{pic_type}_count'] = result[0] if result else 0
            
            # 高画质图片数量
            query = f"SELECT COUNT(*) FROM {self.table_name} WHERE {pic_type}_status = '高画质'"
            result = db_context.execute_query(query, fetch_one=True)
            stats[f'{pic_type}_high_quality'] = result[0] if result else 0
            
            # 低画质图片数量
            query = f"SELECT COUNT(*) FROM {self.table_name} WHERE {pic_type}_status = '低画质'"
            result = db_context.execute_query(query, fetch_one=True)
            stats[f'{pic_type}_low_quality'] = result[0] if result else 0
        
        return stats
    
    def batch_update_picture_status(self, updates: List[Dict[str, Any]]) -> int:
        """
        批量更新图片状态
        
        Args:
            updates: 更新数据列表，每个元素包含movie_id和要更新的字段
            
        Returns:
            更新的记录数量
        """
        if not updates:
            return 0
        
        updated_count = 0
        try:
            with db_context.get_cursor(auto_commit=False) as cursor:
                for update_data in updates:
                    movie_id = update_data.pop('movie_id')
                    if update_data:  # 确保有要更新的字段
                        existing = self.find_by_movie_id(movie_id)
                        if existing and self.update(existing['id'], update_data):
                            updated_count += 1
                
                cursor.connection.commit()
                self.logger.info(f"成功批量更新 {updated_count} 条图片记录")
                return updated_count
        except Exception as e:
            self.logger.error(f"批量更新图片记录失败: {e}")
            raise

# 创建全局实例
picture_dao = PictureDAO()
