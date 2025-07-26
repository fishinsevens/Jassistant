# backend/image_utils.py
"""
图片处理工具类 - 向后兼容层
使用新的统一图片处理模块
"""
import logging
from image_processing import ImageProcessor, ImageDetails

logger = logging.getLogger(__name__)

def get_image_details(path, settings=None):
    """
    获取图片详细信息，如果失败则返回默认值

    Args:
        path: 图片路径
        settings: 配置信息，用于判断画质标准

    Returns:
        width, height, size_kb, status元组
    """
    processor = ImageProcessor(settings)
    details = processor.get_image_details(path)
    return details.to_tuple()

def get_image_details_obj(path, settings=None):
    """
    获取图片详细信息，返回ImageDetails对象
    
    Args:
        path: 图片路径
        settings: 配置信息，用于判断画质标准
        
    Returns:
        ImageDetails对象
    """
    width, height, size_kb, status = get_image_details(path, settings)
    return ImageDetails(width, height, size_kb, status)

def download_image(image_url, timeout=30, max_retries=3, headers=None):
    """下载图片"""
    processor = ImageProcessor()
    return processor.download_image(image_url, timeout, max_retries)

def crop_poster(img, crop_ratio=1.415):
    """
    裁剪海报，保持指定的高宽比

    Args:
        img: PIL.Image对象
        crop_ratio: 裁剪比例（高/宽）

    Returns:
        裁剪后的PIL.Image对象
    """
    processor = ImageProcessor()
    return processor.crop_poster(img, crop_ratio)

def save_image(img, save_path, quality=95):
    """
    保存图片

    Args:
        img: PIL.Image对象
        save_path: 保存路径
        quality: JPEG质量（1-100）

    Returns:
        是否保存成功
    """
    processor = ImageProcessor()
    return processor.save_image(img, save_path, quality)
