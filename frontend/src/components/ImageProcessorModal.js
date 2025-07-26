import React, { useState, useEffect, useMemo, useRef } from 'react';
import axios from 'axios';
import { XMarkIcon, ArrowPathIcon, PhotoIcon } from '@heroicons/react/24/solid';

const WATERMARK_CONFIG = {
  resolution: { name: '分辨率', options: ['无', '4K', '8K'], type: 'radio' },
  subtitle: { name: '字幕', options: ['中字'], type: 'checkbox' },
  mosaic: { name: '马赛克', options: ['无', '有码', '破解', '流出', '无码'], type: 'radio' },
};
const WATERMARK_FILENAME_MAP = { '4K': '4k', '8K': '8k', '中字': 'subs', '破解': 'cracked', '流出': 'leaked', '无码': 'uncensored', '有码': 'mosaic' };

function ImageProcessorModal({ data, onClose }) {
  const { item_id, image_url, image_type, bangou, base_path, localFile } = data;
  const [isProcessing, setIsProcessing] = useState(false);
  const [watermarks, setWatermarks] = useState({ resolution: null, subtitle: null, mosaic: null });
  const [settings, setSettings] = useState({});
  const [cropPoster, setCropPoster] = useState(true);
  const [imageDimensions, setImageDimensions] = useState({ width: 0, height: 0, naturalWidth: 0, naturalHeight: 0, ratio: 1 });
  const imageRef = useRef(null);
  const containerRef = useRef(null);
  const fileInputRef = useRef(null);
  const [currentImageUrl, setCurrentImageUrl] = useState(image_url);
  const [isLocalImage, setIsLocalImage] = useState(!!localFile);
  const [localImageFile, setLocalImageFile] = useState(localFile || null);

  useEffect(() => {
    const fetchSettings = () => {
      axios.get('/api/settings').then(res => {
        // 兼容新旧API格式
        const settingsData = res.data.settings || res.data;
        setSettings(settingsData);
      });
    };

    fetchSettings();
  }, []);

  // 处理传入的本地文件
  useEffect(() => {
    if (localFile) {
      previewLocalImage(localFile);
    }
  }, [localFile]);

  const handleImageLoad = () => {
    if (imageRef.current) {
      // 使用 setTimeout 确保图片完全渲染后再获取尺寸
      setTimeout(() => {
        if (imageRef.current) {
          const rect = imageRef.current.getBoundingClientRect();
          setImageDimensions({
            width: rect.width,
            height: rect.height,
            naturalWidth: imageRef.current.naturalWidth,
            naturalHeight: imageRef.current.naturalHeight,
            ratio: rect.height / imageRef.current.naturalHeight
          });
        }
      }, 100);
    }
  };

  const handleWatermarkChange = (category, value) => {
    setWatermarks(prev => {
      const newWatermarks = { ...prev };
      if (WATERMARK_CONFIG[category].type === 'radio') {
        newWatermarks[category] = (prev[category] === value || value === '无') ? null : value;
      } else {
        newWatermarks[category] = prev[category] ? null : value;
      }
      return newWatermarks;
    });
  };

  const watermarkPreviews = useMemo(() => {
    // 使用与后端相同的逻辑处理水印列表
    const finalWms = [];
    const allWatermarks = Object.values(watermarks).filter(Boolean);

    if (allWatermarks.includes('4K')) finalWms.push('4K');
    else if (allWatermarks.includes('8K')) finalWms.push('8K');
    
    if (allWatermarks.includes('中字')) finalWms.push('中字');
    
    const mosaicPriority = ['有码', '破解', '流出', '无码'];
    for (const wm of mosaicPriority) {
      if (allWatermarks.includes(wm)) {
        finalWms.push(wm);
        break;
      }
    }
    
    return finalWms;
  }, [watermarks]);

  const cropPreviewStyle = useMemo(() => {
    if (!imageDimensions.height || !imageDimensions.naturalWidth || !settings.poster_crop_ratio || !(image_type === 'poster' || (image_type === 'fanart' && cropPoster))) {
      return { display: 'none' };
    }

    const cropRatio = parseFloat(settings.poster_crop_ratio) || 1.419;
    const targetRatio = 1 / cropRatio;
    const naturalRatio = imageDimensions.naturalWidth / imageDimensions.naturalHeight;

    if (naturalRatio <= targetRatio) {
      return { display: 'none' }; // 不需要裁剪
    }

    // 计算裁剪后的自然尺寸
    const croppedNaturalWidth = targetRatio * imageDimensions.naturalHeight;
    const naturalLeftOffset = imageDimensions.naturalWidth - croppedNaturalWidth;

    // 计算显示缩放比例
    const displayScale = imageDimensions.width / imageDimensions.naturalWidth;

    // 将自然尺寸转换为显示尺寸
    const previewWidth = croppedNaturalWidth * displayScale;
    const leftOffset = naturalLeftOffset * displayScale;

    return {
      position: 'absolute',
      left: `${leftOffset}px`,
      top: '0',
      width: `${previewWidth}px`,
      height: '100%',
      border: '3px dashed rgba(255, 255, 255, 0.9)',
      backgroundColor: 'rgba(0, 0, 0, 0.4)',
      pointerEvents: 'none',
      boxShadow: 'inset 0 0 10px rgba(255, 255, 255, 0.3)'
    };
  }, [imageDimensions, settings.poster_crop_ratio, image_type, cropPoster]);

  // 生成与后端处理逻辑一致的水印预览样式
  const generateWatermarkStyles = useMemo(() => {
    if (!imageDimensions.height || watermarkPreviews.length === 0) return [];
    
    const scaleRatio = parseInt(settings.watermark_scale_ratio || 9);
    const hOffset = parseInt(settings.watermark_horizontal_offset || 0);
    const vOffset = parseInt(settings.watermark_vertical_offset || 0);
    const spacing = parseInt(settings.watermark_spacing || 10);
    
    // 计算真实的缩放比例 - 这是显示图片与原始图片的比例
    // object-contain 模式下图片会保持原始比例缩放，需要使用正确的缩放因子
    const displayScale = imageDimensions.ratio || imageDimensions.height / imageDimensions.naturalHeight;
    
    // 根据缩放比例调整所有参数
    const adjustedHOffset = hOffset * displayScale;
    const adjustedVOffset = vOffset * displayScale;
    const adjustedSpacing = spacing * displayScale;
    
    let currentX = adjustedHOffset;
    const watermarkStyles = [];
    
    // 为每个水印计算位置和大小
    for (const wm of watermarkPreviews) {
      // 按照后端逻辑计算水印高度，但应用显示缩放
      const height = imageDimensions.naturalHeight / scaleRatio * displayScale;
      
      watermarkStyles.push({
        key: wm,
        filename: WATERMARK_FILENAME_MAP[wm],
        style: {
          position: 'absolute',
          top: `${adjustedVOffset}px`,
          left: `${currentX}px`,
          height: `${height}px`,
          width: 'auto'
        }
      });
      
      // 使用准确的水印宽高比 769×374 ≈ 2.06:1
      const estimatedWidth = height * 2.06;
      currentX += estimatedWidth + adjustedSpacing;
    }
    
    return watermarkStyles;
  }, [watermarkPreviews, imageDimensions, settings]);

  // 上传并处理本地图片
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    setLocalImageFile(file);
    setIsLocalImage(true);
    
    // 创建临时URL显示图片
    const tempUrl = URL.createObjectURL(file);
    setCurrentImageUrl(tempUrl);
    
    // 预览水印处理
    previewLocalImage(file);
  };
  
  const previewLocalImage = async (file) => {
    if (!file) return;

    // 直接设置本地文件，不创建 blob URL
    setLocalImageFile(file);
    const tempUrl = URL.createObjectURL(file);
    setCurrentImageUrl(tempUrl);

    // 重新计算图片尺寸以便裁剪预览
    const img = new Image();
    img.onload = () => {
      // 先设置自然尺寸，显示尺寸会在 handleImageLoad 中更新
      setImageDimensions(prev => ({
        ...prev,
        naturalWidth: img.naturalWidth,
        naturalHeight: img.naturalHeight
      }));
    };
    img.src = tempUrl;
  };
  
  const handleClickUpload = () => {
    fileInputRef.current?.click();
  };

  const handleProcess = async () => {
    if (isProcessing) return;
    setIsProcessing(true);
    
    if (localImageFile) {
      // 本地文件上传处理
      const formData = new FormData();
      formData.append('image', localImageFile);
      
      const finalWatermarks = Object.values(watermarks).filter(Boolean);
      finalWatermarks.forEach(wm => {
        formData.append('watermarks[]', wm);
      });
      
      if (item_id) formData.append('movie_id', item_id);
      formData.append('target_type', image_type);
      formData.append('crop_for_poster', image_type === 'poster' || (image_type === 'fanart' && cropPoster));
      
      // 设置保存路径
      if (image_type === 'fanart' && cropPoster) {
        // 处理 fanart 和 poster
        const basePath = base_path || '';
        const fanartPath = `${basePath}-fanart.jpg`;
        formData.append('save_path', fanartPath);
        
        try {
          await axios.post('/api/process/upload-image', formData);
          
          // 处理 poster
          const posterFormData = new FormData();
          posterFormData.append('image', localImageFile);
          finalWatermarks.forEach(wm => {
            posterFormData.append('watermarks[]', wm);
          });
          if (item_id) posterFormData.append('movie_id', item_id);
          posterFormData.append('target_type', 'poster');
          posterFormData.append('crop_for_poster', "true");
          posterFormData.append('save_path', `${basePath}-poster.jpg`);
          
          await axios.post('/api/process/upload-image', posterFormData);
          
          // 处理 thumb
          const thumbFormData = new FormData();
          thumbFormData.append('image', localImageFile);
          finalWatermarks.forEach(wm => {
            thumbFormData.append('watermarks[]', wm);
          });
          if (item_id) thumbFormData.append('movie_id', item_id);
          thumbFormData.append('target_type', 'thumb');
          thumbFormData.append('crop_for_poster', "false");
          thumbFormData.append('save_path', `${basePath}-thumb.jpg`);
          
          await axios.post('/api/process/upload-image', thumbFormData);
          
          alert('处理成功');
          onClose(true);
        } catch (error) {
          alert(`处理失败: ${error.response?.data?.message || error.message}`);
        }
      } else {
        // 单个图片处理
        const savePath = base_path ? `${base_path}-${image_type}.jpg` : '';
        if (savePath) formData.append('save_path', savePath);
        
        try {
          await axios.post('/api/process/upload-image', formData);
          alert('处理成功');
          onClose(true);
        } catch (error) {
          alert(`处理失败: ${error.response?.data?.message || error.message}`);
        }
      }
    } else if (image_url && !image_url.startsWith('blob:')) {
      // 远程图片处理逻辑（排除blob URL）
      const finalWatermarks = Object.values(watermarks).filter(Boolean);

      if (image_type === 'fanart' && cropPoster) {
        // 处理 fanart 和 poster
        try {
          await axios.post('/api/process/fanart-and-thumb', {
            item_id,
            image_url,
            watermarks: finalWatermarks,
            crop_poster: cropPoster,
            base_path
          });
          alert('处理成功');
          onClose(true);
        } catch (error) {
          alert(`处理失败: ${error.response?.data?.message || error.message}`);
        }
      } else if (image_type === 'poster') {
        // 处理 poster
        try {
          await axios.post('/api/process/poster', {
            item_id,
            image_url,
            watermarks: finalWatermarks,
            crop: false,
            base_path
          });
          alert('处理成功');
          onClose(true);
        } catch (error) {
          alert(`处理失败: ${error.response?.data?.message || error.message}`);
        }
      }
    } else {
      // 没有有效的图片源
      alert('请选择有效的图片进行处理');
    }

    setIsProcessing(false);
  };

  // 当窗口大小变化时重新计算尺寸
  useEffect(() => {
    const handleResize = () => {
      if (imageRef.current) {
        const rect = imageRef.current.getBoundingClientRect();
        setImageDimensions(prev => ({
          ...prev,
          width: rect.width,
          height: rect.height
        }));
      }
    };
    
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex justify-center items-center z-50 p-4">
      <div className="bg-[var(--color-secondary-bg)] rounded-lg shadow-xl w-full max-w-5xl max-h-full flex flex-col">
        <div className="flex justify-between items-center p-4 border-b border-[var(--color-border)]">
          <h2 className="text-xl font-bold text-[var(--color-primary-text)]">处理图片 - {bangou}</h2>
          <button onClick={() => onClose(false)} className="text-[var(--color-secondary-text)] hover:text-[var(--color-primary-text)]">
            <XMarkIcon className="h-6 w-6" />
          </button>
        </div>
        <div className="flex-grow flex flex-col md:flex-row gap-4 p-4 overflow-y-auto">
          <div className="md:w-3/4 bg-black rounded-md flex justify-center items-center">
            <div ref={containerRef} className="relative inline-block max-w-full max-h-[75vh]">
              <img 
                ref={imageRef} 
                onLoad={handleImageLoad} 
                src={currentImageUrl} 
                alt="预览" 
                className="max-w-full max-h-[75vh] object-contain block" 
              />
              {image_type === 'fanart' && cropPoster && <div style={cropPreviewStyle} />}
              <div className="absolute top-0 left-0 w-full h-full pointer-events-none">
                {generateWatermarkStyles.map(wm => (
                  <img 
                    key={wm.key} 
                    src={`/api/watermarks/${wm.filename}.png`} 
                    alt={wm.key} 
                    style={wm.style}
                  />
                ))}
              </div>
            </div>
          </div>
          <div className="md:w-1/4 flex flex-col gap-6">
            {/* 添加本地上传按钮 */}
            <div className="mb-2">
              <button 
                onClick={handleClickUpload}
                className="flex items-center justify-center gap-2 w-full bg-[var(--color-primary-accent)] text-white py-2 rounded-md hover:bg-opacity-80"
              >
                <PhotoIcon className="h-5 w-5" />
                上传本地图片
              </button>
              <input 
                type="file" 
                ref={fileInputRef}
                className="hidden" 
                accept="image/*"
                onChange={handleFileChange}
              />
              {isLocalImage && <div className="text-xs text-[var(--color-secondary-text)] mt-1">已选择本地图片</div>}
            </div>
            
            {Object.entries(WATERMARK_CONFIG).map(([key, config]) => (
              <div key={key}>
                <h4 className="font-bold text-[var(--color-primary-text)] mb-2">{config.name}</h4>
                <div className="flex flex-col gap-2">
                  {config.options.map(opt => (
                    <label key={opt} className="flex items-center gap-2 bg-[var(--color-sidebar-bg)] p-2 rounded-md cursor-pointer hover:bg-[var(--color-secondary-bg)]">
                      <input type={config.type} name={key} value={opt} checked={watermarks[key] === opt} onChange={() => handleWatermarkChange(key, opt)} className="h-4 w-4 rounded bg-[var(--color-secondary-bg)] border-[var(--color-border)] text-[var(--color-primary-accent)] focus:ring-[var(--color-primary-accent)]" />
                      <span className="text-[var(--color-primary-text)]">{opt}</span>
                    </label>
                  ))}
                </div>
              </div>
            ))}
            <div className="mt-auto space-y-2">
              {image_type === 'fanart' && (
                <>
                  <label className="flex items-center gap-2 bg-[var(--color-sidebar-bg)] p-2 rounded-md cursor-pointer hover:bg-[var(--color-secondary-bg)]">
                    <input type="checkbox" checked={cropPoster} onChange={(e) => setCropPoster(e.target.checked)} className="h-4 w-4 rounded bg-[var(--color-secondary-bg)] border-[var(--color-border)] text-[var(--color-primary-accent)] focus:ring-[var(--color-primary-accent)]" />
                    <span className="text-[var(--color-primary-text)]">同时右侧裁剪为Poster</span>
                  </label>
                  <button onClick={handleProcess} disabled={isProcessing} className="w-full bg-[var(--color-secondary-accent)] text-white py-2 rounded-md flex justify-center items-center gap-2 disabled:opacity-50">
                    {isProcessing && <ArrowPathIcon className="h-5 w-5 animate-spin" />} 保存处理
                  </button>
                </>
              )}
              {image_type === 'poster' && (
                <button onClick={handleProcess} disabled={isProcessing} className="w-full bg-[var(--color-primary-accent)] text-white py-2 rounded-md flex justify-center items-center gap-2 disabled:opacity-50">
                  {isProcessing && <ArrowPathIcon className="h-5 w-5 animate-spin" />} 保存为 Poster
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ImageProcessorModal;
