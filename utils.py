# backend/utils.py
import os
import logging
import shutil
from werkzeug.utils import secure_filename
from pathlib import Path
import re # Added for get_safe_filename

logger = logging.getLogger(__name__)

# 路径相关工具函数
def is_safe_path(path, media_root):
    """
    检查请求路径是否在允许的媒体根目录内
    
    Args:
        path: 要检查的路径
        media_root: 媒体根目录
        
    Returns:
        bool: 如果路径安全则返回True，否则返回False
    """
    # 特殊处理：允许访问cover_cache目录
    if '/cover_cache/' in path or path.endswith('/cover_cache'):
        return True
    
    # 确保路径已规范化
    path = os.path.normpath(path)
    media_root = os.path.normpath(media_root)
    
    # 处理根目录本身的访问
    if path == media_root:
        return True
    
    # 确保path是绝对路径
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    
    # 确保media_root是绝对路径
    if not os.path.isabs(media_root):
        media_root = os.path.abspath(media_root)
    
    # 尝试计算commonpath以检查路径是否在media_root内
    try:
        is_allowed = os.path.commonpath([media_root, path]).startswith(media_root)
        # 记录调试信息
        if not is_allowed:
            logger.debug(f"权限拒绝: 请求路径 '{path}' 不在媒体根目录 '{media_root}' 内")
        return is_allowed
    except ValueError as e:
        # 可能因为驱动器不同等原因导致commonpath失败
        logger.warning(f"路径安全检查失败: {str(e)}, 媒体根路径: {media_root}, 请求路径: {path}")
        return False

def get_safe_filename(strm_name):
    """获取安全的文件名，避免非法字符
    
    werkzeug的secure_filename会过滤掉所有非ASCII字符（包括中文），
    所以我们需要做一个自定义版本来保留中文字符
    """
    if not strm_name:
        return "unknown"
    
    # 保留中文和字母数字，替换常见的非法字符
    safe_name = strm_name
    # 替换文件系统非法字符为短横线
    safe_name = re.sub(r'[\\/*?:"<>|]', '-', safe_name)
    # 替换多个连续短横线为单个短横线
    safe_name = re.sub(r'-+', '-', safe_name)
    # 移除首尾的空格和点
    safe_name = safe_name.strip('. ')
    
    if not safe_name:
        logger.warning(f"缓存封面警告: 使用了通用名称，原始名称为 '{strm_name}'")
        return "unknown"
    
    return safe_name

def ensure_dir_exists(directory):
    """确保目录存在，如果不存在则创建"""
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        logger.debug(f"创建目录: {directory}")
    return directory

# 图片处理相关工具函数
def get_file_extension(filename):
    """获取文件扩展名（小写）"""
    return os.path.splitext(filename.lower())[1] if filename else ""

def is_image_file(filename):
    """检查文件是否为支持的图片格式"""
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    return get_file_extension(filename) in allowed_extensions

def get_base_path_from_file(file_path):
    """从文件路径中获取不含扩展名的基础路径"""
    return os.path.splitext(file_path)[0]

# HTTP相关工具函数
HTTP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
}

# 重命名和文件操作函数
def safe_rename(old_path, new_path):
    """安全地重命名文件，处理目标文件已存在的情况"""
    try:
        # 如果目标路径已存在，先备份
        if os.path.exists(new_path):
            backup_path = f"{new_path}.bak"
            logger.info(f"目标路径已存在，创建备份: {backup_path}")
            shutil.copy2(new_path, backup_path)
        
        # 执行重命名
        os.rename(old_path, new_path)
        logger.info(f"重命名成功: {old_path} -> {new_path}")
        return True, ""
    except Exception as e:
        logger.error(f"重命名失败: {str(e)}")
        return False, str(e)

def safe_copy(src_path, dest_path):
    """安全地复制文件，处理目标文件已存在的情况"""
    try:
        # 如果目标路径已存在，先备份
        if os.path.exists(dest_path):
            backup_path = f"{dest_path}.bak"
            logger.info(f"目标路径已存在，创建备份: {backup_path}")
            shutil.copy2(dest_path, backup_path)
        
        # 确保目标目录存在
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        # 复制文件
        shutil.copy2(src_path, dest_path)
        logger.info(f"复制成功: {src_path} -> {dest_path}")
        return True, ""
    except Exception as e:
        logger.error(f"复制失败: {str(e)}")
        return False, str(e)

def safe_delete(path):
    """安全地删除文件或目录，处理可能的异常"""
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
            logger.info(f"删除目录成功: {path}")
        else:
            os.remove(path)
            logger.info(f"删除文件成功: {path}")
        return True, ""
    except Exception as e:
        logger.error(f"删除失败: {str(e)}")
        return False, str(e) 