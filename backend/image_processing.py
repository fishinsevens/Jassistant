# backend/image_processing.py
"""
统一的图片处理模块
整合了图片下载、处理、水印添加等功能
"""
import os
import logging
from PIL import Image
from io import BytesIO
import time
from typing import List, Dict, Any, Optional, Tuple
from http_client import http_client

logger = logging.getLogger(__name__)

# 水印文件配置
WATERMARK_FILES = { 
    "4K": "/app/assets/4k.png", 
    "8K": "/app/assets/8k.png", 
    "中字": "/app/assets/subs.png", 
    "破解": "/app/assets/cracked.png", 
    "流出": "/app/assets/leaked.png", 
    "无码": "/app/assets/uncensored.png",
    "有码": "/app/assets/mosaic.png"
}

# 水印优先级排序
MOSAIC_PRIORITY = ['有码', '破解', '流出', '无码']

class ImageDetails:
    """图片详细信息类"""
    def __init__(self, width=None, height=None, size_kb=None, status='未知'):
        self.width = width
        self.height = height
        self.size_kb = size_kb
        self.status = status
    
    def to_dict(self):
        return {
            'width': self.width,
            'height': self.height,
            'size_kb': self.size_kb,
            'status': self.status
        }
    
    def to_tuple(self):
        """返回元组格式，保持向后兼容"""
        return (self.width, self.height, self.size_kb, self.status)

    def __str__(self):
        return f"{self.width}x{self.height}, {self.size_kb}KB, {self.status}"

class ImageProcessor:
    """图片处理器"""
    
    def __init__(self, settings: Optional[Dict[str, Any]] = None):
        """
        初始化图片处理器
        
        Args:
            settings: 配置信息
        """
        self.settings = settings or {}
        self.logger = logger
    
    def get_image_details(self, path: str) -> ImageDetails:
        """
        获取图片详细信息
        
        Args:
            path: 图片路径
            
        Returns:
            ImageDetails对象
        """
        if not path or not os.path.exists(path): 
            return ImageDetails()
        
        try:
            with Image.open(path) as img: 
                width, height = img.size
            size_in_kb = round(os.path.getsize(path) / 1024, 2)
            
            # 从配置中获取判断标准
            if self.settings:
                min_height = self.settings.get('high_quality_min_height', 800)
                min_width = self.settings.get('high_quality_min_width', 450)
                min_size_kb = self.settings.get('high_quality_min_size_kb', 50)
                
                # 综合判断画质
                is_high_quality = (height >= min_height and 
                                  width >= min_width and 
                                  size_in_kb >= min_size_kb)
                
                status = "高画质" if is_high_quality else "低画质"
            else:
                status = "未知"
            
            self.logger.debug(f"图片质量判断 - 路径: {path}, 尺寸: {width}x{height}, 大小: {size_in_kb}KB, 状态: {status}")
            return ImageDetails(width, height, size_in_kb, status)
            
        except Exception as e:
            self.logger.error(f"无法处理图片 {path}: {e}")
            return ImageDetails(status='处理失败')
    
    def download_image(self, image_url: str, timeout: int = 30, max_retries: int = 3) -> Optional[Image.Image]:
        """
        下载图片
        
        Args:
            image_url: 图片URL
            timeout: 超时时间
            max_retries: 最大重试次数
            
        Returns:
            PIL Image对象或None
        """
        # 处理本地文件路径
        if image_url.startswith('file://'):
            local_path = image_url[7:]  # 移除 'file://' 前缀
            try:
                return Image.open(local_path).convert("RGB")
            except Exception as e:
                self.logger.error(f"无法打开本地文件 {local_path}: {e}")
                return None
        
        # 处理 blob URL
        if image_url.startswith('blob:'):
            self.logger.error(f"无法处理 blob URL: {image_url}")
            return None
        
        # 下载网络图片
        try:
            response = http_client.get(
                image_url, 
                session_name='image',
                timeout=timeout,
                stream=True
            )
            response.raise_for_status()
            return Image.open(BytesIO(response.content)).convert("RGB")
            
        except Exception as e:
            self.logger.error(f"下载图片失败 {image_url}: {e}")
            return None
    
    def crop_poster(self, img: Image.Image, crop_ratio: float = 1.415) -> Image.Image:
        """
        裁剪海报图片
        
        Args:
            img: PIL Image对象
            crop_ratio: 裁剪比例 (宽/高)
            
        Returns:
            裁剪后的PIL Image对象
        """
        try:
            width, height = img.size
            current_ratio = width / height
            
            if current_ratio > crop_ratio:
                # 图片太宽，需要裁剪宽度
                new_width = int(height * crop_ratio)
                left = (width - new_width) // 2
                right = left + new_width
                img = img.crop((left, 0, right, height))
                self.logger.debug(f"裁剪宽度: {width}x{height} -> {new_width}x{height}")
            elif current_ratio < crop_ratio:
                # 图片太高，需要裁剪高度
                new_height = int(width / crop_ratio)
                top = (height - new_height) // 2
                bottom = top + new_height
                img = img.crop((0, top, width, bottom))
                self.logger.debug(f"裁剪高度: {width}x{height} -> {width}x{new_height}")
            
            return img
            
        except Exception as e:
            self.logger.error(f"裁剪图片失败: {e}")
            return img
    
    def save_image(self, img: Image.Image, save_path: str, quality: int = 95) -> bool:
        """
        保存图片
        
        Args:
            img: PIL Image对象
            save_path: 保存路径
            quality: JPEG质量（1-100）
            
        Returns:
            是否保存成功
        """
        try:
            # 确保目标目录存在
            target_dir = os.path.dirname(save_path)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
                self.logger.info(f"创建目标目录: {target_dir}")
            
            # 保存处理后的图像
            img.save(save_path, "JPEG", quality=quality)
            self.logger.info(f"图片成功保存到: {save_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存图片失败 {save_path}: {e}")
            return False
    
    def add_watermarks(self, base_image: Image.Image, watermarks: List[str]) -> Image.Image:
        """
        添加水印到图片
        
        Args:
            base_image: 基础图片
            watermarks: 水印列表
            
        Returns:
            添加水印后的图片
        """
        if not watermarks: 
            return base_image
        
        # 记录水印设置
        self.logger.info(f"添加水印 - 原始水印列表: {watermarks}")
        self.logger.info(f"水印设置 - 比例: {self.settings.get('watermark_scale_ratio')}, "
                        f"横向: {self.settings.get('watermark_horizontal_offset')}, "
                        f"纵向: {self.settings.get('watermark_vertical_offset')}, "
                        f"间距: {self.settings.get('watermark_spacing')}")
        
        # 筛选要添加的水印
        final_wms = []
        
        # 分辨率水印 (只添加一个)
        if '4K' in watermarks: 
            final_wms.append('4K')
        elif '8K' in watermarks: 
            final_wms.append('8K')
        
        # 字幕水印
        if '中字' in watermarks: 
            final_wms.append('中字')
        
        # 马赛克相关水印 (按优先级只添加一个)
        for mosaic_type in MOSAIC_PRIORITY:
            if mosaic_type in watermarks:
                final_wms.append(mosaic_type)
                break
        
        self.logger.info(f"最终水印列表: {final_wms}")
        
        if not final_wms:
            return base_image
        
        try:
            # 复制基础图片
            result_img = base_image.copy()
            
            # 获取水印设置
            scale_ratio = self.settings.get('watermark_scale_ratio', 12)
            h_offset = self.settings.get('watermark_horizontal_offset', 12)
            v_offset = self.settings.get('watermark_vertical_offset', 6)
            spacing = self.settings.get('watermark_spacing', 6)
            
            # 计算水印大小
            base_width, base_height = result_img.size
            watermark_height = base_height // scale_ratio
            
            # 添加每个水印
            current_x = h_offset
            for wm_name in final_wms:
                wm_path = WATERMARK_FILES.get(wm_name)
                if not wm_path or not os.path.exists(wm_path):
                    self.logger.warning(f"水印文件不存在: {wm_path}")
                    continue
                
                try:
                    with Image.open(wm_path) as wm_img:
                        # 调整水印大小
                        wm_ratio = wm_img.width / wm_img.height
                        wm_width = int(watermark_height * wm_ratio)
                        wm_resized = wm_img.resize((wm_width, watermark_height), Image.Resampling.LANCZOS)
                        
                        # 计算位置
                        y_pos = base_height - watermark_height - v_offset
                        
                        # 粘贴水印
                        if wm_resized.mode == 'RGBA':
                            result_img.paste(wm_resized, (current_x, y_pos), wm_resized)
                        else:
                            result_img.paste(wm_resized, (current_x, y_pos))
                        
                        self.logger.info(f"添加水印: {wm_name} 位置: ({current_x}, {y_pos}) 大小: {wm_width}x{watermark_height}")
                        
                        # 更新下一个水印的位置
                        current_x += wm_width + spacing
                        
                except Exception as e:
                    self.logger.error(f"添加水印失败 {wm_name}: {e}")
                    continue
            
            return result_img
            
        except Exception as e:
            self.logger.error(f"添加水印过程失败: {e}")
            return base_image
    
    def process_image_from_url(self, image_url: str, save_path: str, target_type: str, 
                              watermarks: List[str] = None, crop_for_poster: bool = False) -> Tuple[bool, str]:
        """
        处理图像：下载、裁剪、添加水印并保存
        
        Args:
            image_url: 图片URL
            save_path: 保存路径
            target_type: 目标类型
            watermarks: 水印列表
            crop_for_poster: 是否裁剪海报
            
        Returns:
            (是否成功, 错误信息)
        """
        try:
            # 下载图片
            img = self.download_image(image_url)
            if img is None:
                return False, "下载图片失败"
            
            # 裁剪海报（如果需要）
            if crop_for_poster:
                crop_ratio = float(self.settings.get('poster_crop_ratio', 1.415))
                img = self.crop_poster(img, crop_ratio)
            
            # 添加水印
            if watermarks:
                img = self.add_watermarks(img, watermarks)
            
            # 保存图片
            if self.save_image(img, save_path):
                return True, ""
            else:
                return False, "保存图片失败"
                
        except Exception as e:
            error_msg = f"处理图片失败: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

# 向后兼容的函数
def get_image_details(path, settings=None):
    """向后兼容：获取图片详细信息"""
    processor = ImageProcessor(settings)
    details = processor.get_image_details(path)
    return details.to_tuple()

def download_image(image_url, timeout=30, max_retries=3, headers=None):
    """向后兼容：下载图片"""
    processor = ImageProcessor()
    return processor.download_image(image_url, timeout, max_retries)

def crop_poster(img, crop_ratio=1.415):
    """向后兼容：裁剪海报"""
    processor = ImageProcessor()
    return processor.crop_poster(img, crop_ratio)

def save_image(img, save_path, quality=95):
    """向后兼容：保存图片"""
    processor = ImageProcessor()
    return processor.save_image(img, save_path, quality)
