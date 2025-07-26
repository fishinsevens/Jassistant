# backend/db_manager.py
import sqlite3
import os
from flask import current_app
import time
import threading

DB_PATH = os.path.join('db', 'media.db')

# 添加初始化标记，确保只初始化一次
_DB_INITIALIZED = False

# 数据库连接池
_connection_pool = []
_pool_lock = threading.Lock()
_MAX_POOL_SIZE = 5
_MAX_RETRY_COUNT = 3

# 连接池统计信息
_pool_stats = {
    'total_connections_created': 0,
    'total_connections_reused': 0,
    'total_connections_closed': 0,
    'current_pool_size': 0,
    'peak_pool_size': 0
}

# SQL语句常量
SQL_CREATE_MOVIES_TABLE = '''
CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY, 
    item_path TEXT NOT NULL UNIQUE, 
    bangou TEXT, 
    title TEXT, 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
'''

SQL_CREATE_PICTURES_TABLE = '''
CREATE TABLE IF NOT EXISTS pictures (
    id INTEGER PRIMARY KEY,
    movie_id INTEGER NOT NULL UNIQUE,
    poster_path TEXT,
    poster_width INTEGER,
    poster_height INTEGER,
    poster_size_kb REAL,
    poster_status TEXT,
    fanart_path TEXT,
    fanart_width INTEGER,
    fanart_height INTEGER,
    fanart_size_kb REAL,
    fanart_status TEXT,
    thumb_path TEXT,
    thumb_width INTEGER,
    thumb_height INTEGER,
    thumb_size_kb REAL,
    thumb_status TEXT,
    FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE
);
'''

SQL_CREATE_LINK_CACHE_TABLE = '''
CREATE TABLE IF NOT EXISTS link_verification_cache (
    id INTEGER PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    cid TEXT,
    status_code INTEGER NOT NULL,
    is_valid BOOLEAN NOT NULL,
    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
'''

SQL_CREATE_NFO_DATA_TABLE = '''
CREATE TABLE IF NOT EXISTS nfo_data (
    id INTEGER PRIMARY KEY, 
    movie_id INTEGER NOT NULL, 
    nfo_path TEXT NOT NULL,
    strm_name TEXT NOT NULL, -- 保存完整的strm名称，如MKMP-011-破解-C
    originaltitle TEXT, 
    plot TEXT, 
    originalplot TEXT, 
    tagline TEXT, 
    release_date TEXT, 
    year INTEGER, 
    rating REAL, 
    criticrating REAL,
    FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
    UNIQUE(movie_id, nfo_path),
    UNIQUE(strm_name, nfo_path) -- 使用strm名称和nfo路径作为唯一约束
);
'''

def get_db_connection():
    """获取数据库连接，并设置适当的参数"""
    # 尝试从连接池获取连接
    with _pool_lock:
        if _connection_pool:
            conn = _connection_pool.pop()
            _pool_stats['current_pool_size'] = len(_connection_pool)
            try:
                # 测试连接是否有效
                conn.execute("SELECT 1")
                _pool_stats['total_connections_reused'] += 1
                return conn
            except sqlite3.Error:
                # 连接已失效，创建新连接
                try:
                    conn.close()
                    _pool_stats['total_connections_closed'] += 1
                except:
                    pass
    
    # 创建新连接
    retry_count = 0
    while retry_count < _MAX_RETRY_COUNT:
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            # 启用外键约束
            conn.execute("PRAGMA foreign_keys = ON")
            # 添加性能优化
            conn.execute("PRAGMA journal_mode = WAL")  # 使用WAL模式提高写入性能
            conn.execute("PRAGMA synchronous = NORMAL")  # 降低同步级别提高性能
            conn.execute("PRAGMA cache_size = 10000")   # 增加缓存大小
            # 使用SQLite默认的WAL自动检查点设置
            conn.execute("PRAGMA wal_autocheckpoint = 1000")  # SQLite默认值，平衡性能和及时性

            # 更新统计信息
            _pool_stats['total_connections_created'] += 1
            return conn
        except sqlite3.Error as e:
            retry_count += 1
            if retry_count >= _MAX_RETRY_COUNT:
                current_app.logger.error(f"数据库连接失败，已重试 {retry_count} 次: {e}")
                raise
            current_app.logger.warning(f"数据库连接失败 (尝试 {retry_count}/{_MAX_RETRY_COUNT}): {e}, 将在1秒后重试")
            time.sleep(1)

def return_connection_to_pool(conn):
    """将数据库连接返回到连接池"""
    try:
        # 检查连接是否有效
        conn.execute("SELECT 1")

        # 将连接放回池中
        with _pool_lock:
            if len(_connection_pool) < _MAX_POOL_SIZE:
                _connection_pool.append(conn)
                _pool_stats['current_pool_size'] = len(_connection_pool)
                # 更新峰值统计
                if _pool_stats['current_pool_size'] > _pool_stats['peak_pool_size']:
                    _pool_stats['peak_pool_size'] = _pool_stats['current_pool_size']
                return True
    except Exception as e:
        current_app.logger.warning(f"连接已失效，不放回连接池: {e}")

    # 关闭连接
    try:
        conn.close()
        _pool_stats['total_connections_closed'] += 1
    except:
        pass
    return False

def get_connection_pool_stats():
    """获取连接池统计信息"""
    with _pool_lock:
        stats = _pool_stats.copy()
        stats['current_pool_size'] = len(_connection_pool)
        return stats

def cleanup_connection_pool():
    """清理连接池，关闭所有连接"""
    with _pool_lock:
        while _connection_pool:
            conn = _connection_pool.pop()
            try:
                conn.close()
                _pool_stats['total_connections_closed'] += 1
            except:
                pass
        _pool_stats['current_pool_size'] = 0

def check_column_exists(cursor, table, column):
    """检查表中是否存在特定列"""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [info[1] for info in cursor.fetchall()]
    return column in columns

def migrate_db_if_needed(conn, cursor):
    """执行数据库迁移，如果需要"""
    # 检查是否需要从旧版本迁移
    if not check_column_exists(cursor, 'nfo_data', 'strm_name'):
        current_app.logger.info("检测到需要数据库迁移：添加strm_name字段")
        
        # 创建临时表
        cursor.execute(SQL_CREATE_NFO_DATA_TABLE.replace('nfo_data', 'nfo_data_temp'))
        
        # 从movies表和旧nfo_data表中提取数据进行迁移
        cursor.execute('''
            SELECT n.id, n.movie_id, n.nfo_path, 
                   m.item_path, n.originaltitle, n.plot, 
                   n.originalplot, n.tagline, n.release_date, 
                   n.year, n.rating, n.criticrating
            FROM nfo_data n
            JOIN movies m ON n.movie_id = m.id
        ''')
        
        old_data = cursor.fetchall()
        for row in old_data:
            item_path = row[3]
            strm_name = os.path.splitext(os.path.basename(item_path))[0]
            cursor.execute('''
                INSERT INTO nfo_data_temp (
                    id, movie_id, nfo_path, strm_name, originaltitle, 
                    plot, originalplot, tagline, release_date, 
                    year, rating, criticrating
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (row[0], row[1], row[2], strm_name, row[4], 
                  row[5], row[6], row[7], row[8], row[9], row[10], row[11]))
        
        # 备份关联表数据
        backup_tables = {
            'nfo_actors': 'actor_id',
            'nfo_genres': 'genre_id',
            'nfo_tags': 'tag_id',
            'nfo_sets': 'set_id',
            'nfo_studios': 'studio_id',
            'nfo_labels': 'label_id'
        }
        
        backup_data = {}
        for table, id_field in backup_tables.items():
            cursor.execute(f'SELECT nfo_id, {id_field} FROM {table}')
            backup_data[table] = cursor.fetchall()
            cursor.execute(f'DROP TABLE {table}')
        
        # 删除旧表
        cursor.execute('DROP TABLE nfo_data')
        
        # 重命名新表
        cursor.execute('ALTER TABLE nfo_data_temp RENAME TO nfo_data')
        
        # 重建关联表和恢复数据
        for table, id_field in backup_tables.items():
            ref_table = id_field.split('_')[0] + 's'  # 例如actor_id -> actors
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {table} (
                    nfo_id INTEGER, 
                    {id_field} INTEGER, 
                    FOREIGN KEY(nfo_id) REFERENCES nfo_data(id) ON DELETE CASCADE, 
                    FOREIGN KEY({id_field}) REFERENCES {ref_table}(id) ON DELETE CASCADE, 
                    PRIMARY KEY (nfo_id, {id_field})
                );
            ''')
            
            # 恢复数据
            for nfo_id, ref_id in backup_data[table]:
                cursor.execute(f'INSERT INTO {table} (nfo_id, {id_field}) VALUES (?, ?)', 
                              (nfo_id, ref_id))
            
        current_app.logger.info("数据库迁移完成：已添加strm_name字段并迁移数据")

    # 检查并创建缺失的表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pictures'")
    if not cursor.fetchone():
        current_app.logger.info("创建缺失的pictures表")
        cursor.execute(SQL_CREATE_PICTURES_TABLE)
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pictures_status ON pictures(poster_status, fanart_status);')

    # 检查并创建链接验证缓存表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='link_verification_cache'")
    table_exists = cursor.fetchone()

    if not table_exists:
        # 创建新的简化表结构
        cursor.execute(SQL_CREATE_LINK_CACHE_TABLE)
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_link_cache_url ON link_verification_cache(url);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_link_cache_cid ON link_verification_cache(cid);')
    else:
        # 检查是否需要迁移到新表结构
        if check_column_exists(cursor, 'link_verification_cache', 'expires_at'):
            # 旧表结构，需要迁移
            cursor.execute('''
                CREATE TABLE link_verification_cache_new (
                    id INTEGER PRIMARY KEY,
                    url TEXT NOT NULL UNIQUE,
                    cid TEXT,
                    status_code INTEGER NOT NULL,
                    is_valid BOOLEAN NOT NULL,
                    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')

            # 迁移数据（只保留有效的链接）
            cursor.execute('''
                INSERT INTO link_verification_cache_new (url, status_code, is_valid, verified_at)
                SELECT url, status_code, is_valid, verified_at
                FROM link_verification_cache
                WHERE is_valid = 1
            ''')

            # 删除旧表，重命名新表
            cursor.execute('DROP TABLE link_verification_cache')
            cursor.execute('ALTER TABLE link_verification_cache_new RENAME TO link_verification_cache')

            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_link_cache_url ON link_verification_cache(url);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_link_cache_cid ON link_verification_cache(cid);')
        elif not check_column_exists(cursor, 'link_verification_cache', 'cid'):
            # 添加CID字段
            cursor.execute('ALTER TABLE link_verification_cache ADD COLUMN cid TEXT')

def create_tables(cursor):
    """创建所有表结构"""
    current_app.logger.info("开始初始化数据库表结构...")
    
    # 创建主表
    cursor.execute(SQL_CREATE_MOVIES_TABLE)
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_movies_bangou ON movies(bangou);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_movies_created_at ON movies(created_at);')
    
    cursor.execute(SQL_CREATE_PICTURES_TABLE)
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pictures_status ON pictures(poster_status, fanart_status);')

    # 创建链接验证缓存表
    cursor.execute(SQL_CREATE_LINK_CACHE_TABLE)
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_link_cache_url ON link_verification_cache(url);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_link_cache_expires ON link_verification_cache(expires_at);')

    # 创建NFO数据表
    cursor.execute(SQL_CREATE_NFO_DATA_TABLE)
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_nfo_data_strm_name ON nfo_data(strm_name);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_nfo_data_year ON nfo_data(year);')
    
    # 创建各种辅助表
    entity_tables = {
        'actors': 'actor', 
        'genres': 'genre', 
        'tags': 'tag', 
        'studios': 'studio', 
        'labels': 'label', 
        'sets': 'set'
    }
    
    for table, entity in entity_tables.items():
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {table} (
                id INTEGER PRIMARY KEY, 
                name TEXT UNIQUE NOT NULL
            );
        ''')
        
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS nfo_{entity}s (
                nfo_id INTEGER, 
                {entity}_id INTEGER, 
                FOREIGN KEY(nfo_id) REFERENCES nfo_data(id) ON DELETE CASCADE, 
                FOREIGN KEY({entity}_id) REFERENCES {table}(id) ON DELETE CASCADE, 
                PRIMARY KEY (nfo_id, {entity}_id)
            );
        ''')
    
    # 移除废弃的表
    deprecated_tables = [
        'movie_actors', 'movie_genres', 'movie_tags',
        'movie_sets', 'movie_studios', 'movie_labels'
    ]
    for table in deprecated_tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table};")
    
    current_app.logger.info("数据库表结构初始化完成 (v7)。")

def init_db():
    """初始化数据库结构，确保只执行一次"""
    global _DB_INITIALIZED
    
    # 如果已经初始化过，直接返回
    if _DB_INITIALIZED:
        return
    
    # 确保数据库目录存在
    if not os.path.exists(os.path.dirname(DB_PATH)):
        os.makedirs(os.path.dirname(DB_PATH))

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 开始事务
        cursor.execute("BEGIN TRANSACTION")
        
        # 检查数据库是否已经初始化（通过检查主表是否存在）
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='movies'")
        if cursor.fetchone():
            # 表已存在，只需检查是否需要迁移
            migrate_db_if_needed(conn, cursor)
            conn.commit()
            _DB_INITIALIZED = True
            return_connection_to_pool(conn)
            return
            
        # 数据库尚未初始化，创建所有表
        create_tables(cursor)
    
        # 提交事务
        conn.commit()
        
        # 标记为已初始化
        _DB_INITIALIZED = True
        
        # 将连接放回连接池
        return_connection_to_pool(conn)
    except Exception as e:
        # 发生错误时回滚
        conn.rollback()
        current_app.logger.error(f"数据库初始化失败: {str(e)}", exc_info=True)
        # 关闭连接，不放回连接池
        try:
            conn.close()
        except:
            pass
        raise
