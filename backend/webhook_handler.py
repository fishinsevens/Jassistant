# backend/webhook_handler.py
import os
import re
from flask import current_app
from image_processor import get_image_details
from db_manager import get_db_connection
from nfo_parser import parse_nfo_file

def extract_bangou_from_title(title_str):
    match = re.search(r'([A-Z]{2,5}-\d{2,5})', title_str.upper())
    if match:
        bangou = match.group(1)
        clean_title = title_str.replace(bangou, '').strip()
        return bangou, clean_title
    return "N/A", title_str

def extract_strm_name_from_path(item_path):
    """
    从文件路径中提取strm名称（不包含后缀）
    例如: /weiam/onestrm/NSFW/JAV/M/MKMP/MKMP-011/MKMP-011-破解-C.strm -> MKMP-011-破解-C
    """
    if not item_path:
        return ""
    
    # 获取不带路径的文件名
    basename = os.path.basename(item_path)
    # 移除文件后缀名
    strm_name = os.path.splitext(basename)[0]
    return strm_name

def handle_nfo_mappings(cursor, nfo_id, nfo_data):
    def process_mapping(items, table_name, column_name):
        if not items: return
        if not isinstance(items, list): items = [items]
        item_ids = []
        for item_name in items:
            cursor.execute(f"SELECT id FROM {table_name}s WHERE name = ?", (item_name,))
            row = cursor.fetchone()
            item_ids.append(row['id'] if row else cursor.execute(f"INSERT INTO {table_name}s (name) VALUES (?)", (item_name,)).lastrowid)
        cursor.execute(f"DELETE FROM nfo_{table_name}s WHERE nfo_id = ?", (nfo_id,))
        for item_id in item_ids:
            cursor.execute(f"INSERT INTO nfo_{table_name}s (nfo_id, {column_name}_id) VALUES (?, ?)", (nfo_id, item_id))
    process_mapping(nfo_data.get('actors'), 'actor', 'actor')
    process_mapping(nfo_data.get('genres'), 'genre', 'genre')
    process_mapping(nfo_data.get('tags'), 'tag', 'tag')
    process_mapping(nfo_data.get('sets'), 'set', 'set')
    process_mapping(nfo_data.get('studio'), 'studio', 'studio')
    process_mapping(nfo_data.get('label'), 'label', 'label')

def process_new_item(data):
    item_path = data.get("Item", {}).get("Path")
    item_name = data.get("Item", {}).get("Name")
    if not item_path: return {"success": False, "message": "无效的路径"}
    
    bangou, clean_title = extract_bangou_from_title(item_name)
    strm_name = extract_strm_name_from_path(item_path)  # 获取strm名称
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("INSERT INTO movies (item_path, bangou, title) VALUES (?, ?, ?) ON CONFLICT(item_path) DO UPDATE SET title=excluded.title, bangou=excluded.bangou", (item_path, bangou, clean_title))
        cursor.execute("SELECT id FROM movies WHERE item_path = ?", (item_path,))
        movie_id = cursor.fetchone()['id']
        base_path = os.path.splitext(item_path)[0]
        
        # 检查并记录图片文件的存在状态
        poster_path = f"{base_path}-poster.jpg"
        fanart_path = f"{base_path}-fanart.jpg"
        thumb_path = f"{base_path}-thumb.jpg"
        
        # 记录图片文件状态
        if os.path.exists(poster_path):
            current_app.logger.info(f"找到封面图片: {poster_path}")
        if os.path.exists(fanart_path):
            current_app.logger.info(f"找到背景图片: {fanart_path}")
        if os.path.exists(thumb_path):
            current_app.logger.info(f"找到缩略图: {thumb_path}")
        
        p_w, p_h, p_s_kb, p_stat = get_image_details(poster_path)
        f_w, f_h, f_s_kb, f_stat = get_image_details(fanart_path)
        t_w, t_h, t_s_kb, t_stat = get_image_details(thumb_path)
        cursor.execute("INSERT INTO pictures (movie_id, poster_path, poster_width, poster_height, poster_size_kb, poster_status, fanart_path, fanart_width, fanart_height, fanart_size_kb, fanart_status, thumb_path, thumb_width, thumb_height, thumb_size_kb, thumb_status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(movie_id) DO UPDATE SET poster_path=excluded.poster_path, poster_width=excluded.poster_width, poster_height=excluded.poster_height, poster_size_kb=excluded.poster_size_kb, poster_status=excluded.poster_status, fanart_path=excluded.fanart_path, fanart_width=excluded.fanart_width, fanart_height=excluded.fanart_height, fanart_size_kb=excluded.fanart_size_kb, fanart_status=excluded.fanart_status, thumb_path=excluded.thumb_path, thumb_width=excluded.thumb_width, thumb_height=excluded.thumb_height, thumb_size_kb=excluded.thumb_size_kb, thumb_status=excluded.thumb_status", (movie_id, f"{base_path}-poster.jpg", p_w, p_h, p_s_kb, p_stat, f"{base_path}-fanart.jpg", f_w, f_h, f_s_kb, f_stat, f"{base_path}-thumb.jpg", t_w, t_h, t_s_kb, t_stat))
        
        # 处理NFO文件 - 查找与当前strm同名但扩展名为.nfo的文件
        dir_path = os.path.dirname(item_path)
        abs_dir_path = dir_path
        
        # 跟踪已处理的NFO文件路径，避免处理重复的NFO
        processed_nfo_paths = set()
        
        # 首先尝试查找与strm文件同名的nfo文件（替换后缀）
        nfo_file_name = f"{strm_name}.nfo"
        nfo_file_path = os.path.join(dir_path, nfo_file_name)
        abs_nfo_path = os.path.join(abs_dir_path, nfo_file_name)
        
        if os.path.exists(abs_nfo_path):
            # 找到对应的NFO文件
            current_app.logger.info(f"找到与strm对应的NFO文件: {nfo_file_path}")
            processed_nfo_paths.add(nfo_file_path)
            nfo_data = parse_nfo_file(abs_nfo_path)
            if nfo_data:
                nfo_main_cols = ['originaltitle', 'plot', 'originalplot', 'tagline', 'release_date', 'year', 'rating', 'criticrating']
                nfo_main_vals = [nfo_data.get(col) for col in nfo_main_cols]
                
                # 使用strm_name作为约束字段
                try:
                    cursor.execute(f"INSERT INTO nfo_data (movie_id, nfo_path, strm_name, {', '.join(nfo_main_cols)}) VALUES (?, ?, ?, {', '.join(['?'] * len(nfo_main_cols))}) ON CONFLICT(strm_name, nfo_path) DO UPDATE SET " + ", ".join([f"{col}=excluded.{col}" for col in nfo_main_cols]), 
                                (movie_id, nfo_file_path, strm_name, *nfo_main_vals))
                except Exception as e:
                    current_app.logger.warning(f"插入NFO数据时发生错误: {nfo_file_path} - {str(e)}")
                    
                cursor.execute("SELECT id FROM nfo_data WHERE movie_id = ? AND nfo_path = ?", (movie_id, nfo_file_path))
                nfo_id_row = cursor.fetchone()
                if nfo_id_row:
                    nfo_id = nfo_id_row['id']
                    handle_nfo_mappings(cursor, nfo_id, nfo_data)
        else:
            # 如果没有找到精确匹配的NFO，寻找目录中包含相同番号的NFO文件
            current_app.logger.info(f"未找到与strm完全对应的NFO文件，尝试查找包含番号的NFO")
            for filename in os.listdir(abs_dir_path):
                if bangou.lower() in filename.lower() and filename.lower().endswith('.nfo'):
                    nfo_file_path = os.path.join(dir_path, filename)
                    
                    # 如果此NFO路径已处理过，跳过
                    if nfo_file_path in processed_nfo_paths:
                        continue
                    
                    processed_nfo_paths.add(nfo_file_path)
                    abs_nfo_path = os.path.join(abs_dir_path, filename)
                    
                    nfo_data = parse_nfo_file(abs_nfo_path)
                    if nfo_data:
                        nfo_main_cols = ['originaltitle', 'plot', 'originalplot', 'tagline', 'release_date', 'year', 'rating', 'criticrating']
                        nfo_main_vals = [nfo_data.get(col) for col in nfo_main_cols]
                        
                        # 使用strm_name作为约束字段
                        try:
                            cursor.execute(f"INSERT INTO nfo_data (movie_id, nfo_path, strm_name, {', '.join(nfo_main_cols)}) VALUES (?, ?, ?, {', '.join(['?'] * len(nfo_main_cols))}) ON CONFLICT(strm_name, nfo_path) DO UPDATE SET " + ", ".join([f"{col}=excluded.{col}" for col in nfo_main_cols]), 
                                        (movie_id, nfo_file_path, strm_name, *nfo_main_vals))
                        except Exception as e:
                            current_app.logger.warning(f"插入NFO数据时发生错误: {nfo_file_path} - {str(e)}")
                            continue
                            
                        cursor.execute("SELECT id FROM nfo_data WHERE movie_id = ? AND nfo_path = ?", (movie_id, nfo_file_path))
                        nfo_id_row = cursor.fetchone()
                        if nfo_id_row:
                            nfo_id = nfo_id_row['id']
                            handle_nfo_mappings(cursor, nfo_id, nfo_data)
        
        conn.commit()
        return {"success": True, "message": f"项目 {item_name} 已处理"}
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"处理 {item_name} 时发生严重错误: {e}", exc_info=True)
        return {"success": False, "message": f"数据库错误: {e}"}
    finally:
        conn.close()
