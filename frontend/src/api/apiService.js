// frontend/src/api/apiService.js
import axios from 'axios';

// 创建axios实例，方便统一配置
const api = axios.create({
  baseURL: '/api',
  timeout: 30000, // 30秒超时
  headers: {
    'Content-Type': 'application/json'
  }
});

// 请求拦截器，可以在这里添加加载状态等
api.interceptors.request.use(
  (config) => {
    // 可以在这里添加请求前的处理，如添加token等
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器，统一处理错误
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    // 统一错误处理
    const errorMessage = error.response?.data?.message || error.message;
    console.error('API请求失败:', errorMessage);
    return Promise.reject(error);
  }
);

// 设置相关API
export const settingsAPI = {
  // 获取设置
  getSettings() {
    return api.get('/settings');
  },
  
  // 保存设置
  saveSettings(settings) {
    return api.post('/settings', settings);
  },
  
  // 测试通知
  testNotification() {
    return api.post('/test-notification');
  },
  
  // 更新日志级别
  updateLogLevel(level) {
    return api.post('/update-log-level', { log_level: level });
  },
  
  // 重启容器
  restartContainer() {
    return api.post('/restart-container');
  }
};

// 图片处理相关API
export const imageAPI = {
  // 处理海报
  processPoster(data) {
    return api.post('/process/poster', data);
  },
  
  // 处理背景和缩略图
  processFanartAndThumb(data) {
    return api.post('/process/fanart-and-thumb', data);
  },
  
  // 上传处理图片
  uploadAndProcessImage(formData) {
    return api.post('/process/upload-image', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  }
};

// 获取CID信息
export const cidAPI = {
  // 获取DMM信息
  getDmmInfo(bangou) {
    return api.get(`/get-dmm-info?bangou=${encodeURIComponent(bangou)}`);
  },

  // 手动获取CID信息
  getManualCidInfo(bangou) {
    return api.get(`/get-manual-cid-info?bangou=${encodeURIComponent(bangou.trim())}`);
  },

  // 验证链接有效性
  verifyLinks(links, forceRefresh = false, cid = null) {
    const payload = { links, force_refresh: forceRefresh };
    if (cid) payload.cid = cid;
    return api.post('/verify-links', payload);
  },

  // 清除链接验证缓存
  clearLinkCache(url = null) {
    return api.post('/clear-link-cache', url ? { url } : {});
  },

  // 清除DMM域名缓存
  clearDmmDomainCache() {
    return api.post('/clear-dmm-domain-cache');
  }
};

// 文件管理相关API
export const fileAPI = {
  // 获取文件列表
  listFiles(path, page = 1, page_size = 200, simple = false) {
    return api.get('/files/list', {
      params: { path, page, page_size, simple }
    });
  },
  
  // 重命名文件
  renameFile(path, new_name) {
    return api.post('/files/rename', { path, new_name });
  },
  
  // 删除文件
  deleteFiles(paths) {
    return api.post('/files/delete', { paths });
  },
  
  // 创建目录
  createDirectory(path, name) {
    return api.post('/files/create-dir', { path, name });
  }
};

// 主页和内容相关API
export const contentAPI = {
  // 获取最新项目
  getLatestItems() {
    return api.get('/latest-items');
  },
  
  // 获取低质量项目
  getLowQualityItems(page) {
    return api.get(`/low-quality-items?page=${page}`);
  },
  
  // 跳过项目
  skipItem(itemId) {
    return api.post(`/skip-item/${itemId}`);
  },
  
  // 刷新项目图片
  refreshItemImages(itemId) {
    return api.post(`/refresh-item-images/${itemId}`);
  }
};

// NFO处理相关API
export const nfoAPI = {
  // 获取手工NFO详情
  getHandmadeNfoDetails(nfoPath) {
    return api.get(`/handmade/nfo-details?path=${encodeURIComponent(nfoPath)}`);
  },
  
  // 保存手工NFO
  saveHandmadeNfo(nfoPath, data) {
    return api.post(`/handmade/save-nfo?path=${encodeURIComponent(nfoPath)}`, data);
  },
  
  // 获取影片详情
  getMovieDetails(movieId) {
    return api.get(`/manual/movie-details/${movieId}`);
  },
  
  // 获取NFO内容
  getNfoContent(nfoId) {
    return api.get(`/manual/nfo-content/${nfoId}`);
  },
  
  // 保存NFO内容
  saveNfoContent(nfoId, data) {
    return api.post(`/manual/save-nfo/${nfoId}`, data);
  },
  
  // 查找影片
  findMovie(query) {
    return api.get(`/manual/find-movie?q=${encodeURIComponent(query)}`);
  }
};

// 系统日志相关API
export const logsAPI = {
  // 获取系统日志
  getSystemLogs(maxLines = 500, filterLevel = '') {
    return api.get(`/system-logs?max_lines=${maxLines}${filterLevel ? `&level=${filterLevel}` : ''}`);
  },
  
  // 清除系统日志
  clearSystemLogs() {
    return api.post('/system-logs/clear');
  }
};

// 封面缓存相关API
export const cacheAPI = {
  // 获取封面缓存状态
  getCoverCacheStatus() {
    return api.get('/cover-cache');
  },
  
  // 刷新封面缓存
  refreshCoverCache() {
    return api.post('/cover-cache/refresh');
  },
  
  // 清理封面缓存
  cleanCoverCache() {
    return api.post('/cover-cache/clean');
  }
};

export default {
  settingsAPI,
  imageAPI,
  cidAPI,
  fileAPI,
  contentAPI,
  nfoAPI,
  logsAPI,
  cacheAPI
}; 
