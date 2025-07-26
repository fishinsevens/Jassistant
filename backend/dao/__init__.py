# backend/dao/__init__.py
"""
数据访问对象(DAO)模块
提供统一的数据库访问接口
"""

from .base_dao import BaseDAO
from .movie_dao import MovieDAO, movie_dao
from .picture_dao import PictureDAO, picture_dao
from .nfo_dao import NfoDAO, nfo_dao

__all__ = [
    'BaseDAO',
    'MovieDAO', 'movie_dao',
    'PictureDAO', 'picture_dao',
    'NfoDAO', 'nfo_dao'
]
