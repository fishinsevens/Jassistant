/**
 * 格式化字节大小
 * @param {number} bytes - 字节数
 * @param {number} decimals - 小数位数
 * @returns {string} 格式化后的字节大小
 */
export const formatBytes = (bytes, decimals = 2) => {
  if (!bytes || bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

/**
 * 格式化日期时间
 * @param {number|string|Date} timestamp - 时间戳或日期对象
 * @param {boolean} showTime - 是否显示时间
 * @returns {string} 格式化后的日期时间
 */
export const formatDateTime = (timestamp, showTime = true) => {
  if (!timestamp) return '';
  
  let date;
  if (typeof timestamp === 'number') {
    // 检查是否为秒级时间戳
    if (timestamp < 10000000000) {
      timestamp = timestamp * 1000; // 转换为毫秒
    }
    date = new Date(timestamp);
  } else if (typeof timestamp === 'string') {
    date = new Date(timestamp);
  } else {
    date = timestamp;
  }
  
  if (!(date instanceof Date) || isNaN(date)) return '';
  
  const options = {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  };
  
  if (showTime) {
    options.hour = '2-digit';
    options.minute = '2-digit';
    options.second = '2-digit';
  }
  
  return date.toLocaleString('zh-CN', options);
};

/**
 * 格式化持续时间（秒）
 * @param {number} seconds - 秒数
 * @returns {string} 格式化后的持续时间
 */
export const formatDuration = (seconds) => {
  if (!seconds || seconds <= 0) return '0:00';
  
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
  }
  
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
};

/**
 * 格式化文本为安全的文件名
 * @param {string} text - 原文本
 * @returns {string} 安全的文件名
 */
export const formatSafeFileName = (text) => {
  if (!text) return '';
  
  // 移除非法字符
  return text
    .replace(/[/\\?%*:|"<>]/g, '-') // 替换非法字符
    .replace(/\s+/g, '_'); // 空格替换为下划线
}; 