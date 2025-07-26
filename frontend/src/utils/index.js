// 导出所有格式化工具
export * from './formatters';

// 导出表单帮助工具
export * from './formHelpers';

// 图片路径工具
const PATH_TYPES = {
  COVER_CACHE: 'cover_cache',
  ABSOLUTE: 'absolute',
  RELATIVE: 'relative'
};

/**
 * 分析路径类型
 * @param {string | null} path - 要分析的路径
 * @returns {string} - 路径类型
 */
export const getPathType = (path) => {
  if (!path || typeof path !== 'string') return '';
  
  if (path.includes('/cover_cache/') || path.startsWith('cover_cache/')) {
    return PATH_TYPES.COVER_CACHE;
  }
  
  if (path.startsWith('/')) {
    return PATH_TYPES.ABSOLUTE;
  }
  
  return PATH_TYPES.RELATIVE;
};

/**
 * 根据数据库中的绝对路径，构造可访问的图片API URL。
 * @param {string | null} path - 数据库中存储的文件路径
 * @param {string} placeholder - 图片加载失败或路径为空时显示的占位图URL
 * @returns {string} - 完整的图片URL
 */
export const getImageUrl = (path, placeholder = 'https://placehold.co/400x600/181828/94A1B2?text=No+Image') => {
  // 处理空路径情况
  if (!path || typeof path !== 'string') return placeholder;
  
  try {
    const pathType = getPathType(path);
    
    switch (pathType) {
      case PATH_TYPES.COVER_CACHE:
        // 标准化路径格式
        return path.startsWith('cover_cache/') 
          ? `/api/media/${path}`  // 相对路径格式
          : `/api/media${path}`;  // 绝对路径格式
          
      case PATH_TYPES.ABSOLUTE:
      case PATH_TYPES.RELATIVE:
        return `/api/media${path.startsWith('/') ? path : '/' + path}`;
          
      default:
        return placeholder;
    }
  } catch (error) {
    console.error('构建图片URL时出错:', error, '路径:', path);
    return placeholder;
  }
};

/**
 * 防抖函数 - 确保函数在一定时间内只执行一次
 * @param {Function} func - 要执行的函数
 * @param {number} wait - 延迟执行的毫秒数
 * @param {boolean} immediate - 是否立即执行
 * @returns {Function} - 防抖处理后的函数
 */
export const debounce = (func, wait = 300, immediate = false) => {
  let timeout;
  
  return function executedFunction(...args) {
    const context = this;
    
    const later = function() {
      timeout = null;
      if (!immediate) func.apply(context, args);
    };
    
    const callNow = immediate && !timeout;
    
    clearTimeout(timeout);
    
    timeout = setTimeout(later, wait);
    
    if (callNow) func.apply(context, args);
  };
};

/**
 * 限流函数 - 确保函数在指定时间内最多执行N次
 * @param {Function} func - 要执行的函数
 * @param {number} limit - 时间间隔（毫秒）
 * @returns {Function} - 限流处理后的函数
 */
export const throttle = (func, limit = 100) => {
  let inThrottle;
  return function(...args) {
    const context = this;
    if (!inThrottle) {
      func.apply(context, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
};

/**
 * 图片加载优化器 - 创建优化的图片元素
 * @param {string} src - 图片源URL
 * @param {string} alt - 图片alt文本
 * @param {string} className - 图片CSS类名
 * @returns {HTMLImageElement} - 配置好的图片元素
 */
export const createOptimizedImage = (src, alt = '', className = '') => {
  const img = new Image();
  img.src = src;
  img.alt = alt;
  img.className = className;
  img.loading = 'lazy'; // 懒加载
  img.decoding = 'async'; // 异步解码

  return img;
};
