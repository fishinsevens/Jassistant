# backend/image_processor.py
"""
图片处理模块 - 向后兼容层
使用新的统一图片处理模块
"""
import logging
from image_processing import ImageProcessor, WATERMARK_FILES, MOSAIC_PRIORITY

logger = logging.getLogger(__name__)

def get_image_details(path):
    """获取图片详细信息，如果失败则返回默认值"""
    from config_utils import get_settings

    settings = get_settings()
    processor = ImageProcessor(settings)
    details = processor.get_image_details(path)
    return details.to_tuple()

def add_watermarks(base_image, watermarks, settings):
    """添加水印到图片"""
    processor = ImageProcessor(settings)
    return processor.add_watermarks(base_image, watermarks)

def process_image_from_url(image_url, save_path, target_type, settings, watermarks=[], crop_for_poster=False):
    """处理图像：下载、裁剪、添加水印并保存"""
    processor = ImageProcessor(settings)

    # 应用水印逻辑
    watermark_targets = settings.get('watermark_targets', [])
    logger.info(f"处理水印 {target_type}，应用水印: {watermarks}, 配置的目标类型: {watermark_targets}")

    # 检查当前目标类型是否在水印目标列表中
    should_apply_watermarks = target_type in watermark_targets
    logger.info(f"目标类型 {target_type} 是否应用水印: {should_apply_watermarks}")

    # 只有在需要应用水印时才传递水印列表
    final_watermarks = watermarks if should_apply_watermarks else []

    return processor.process_image_from_url(
        image_url=image_url,
        save_path=save_path,
        target_type=target_type,
        watermarks=final_watermarks,
        crop_for_poster=crop_for_poster
    )
