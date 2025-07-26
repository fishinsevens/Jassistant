import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { getImageUrl } from '../utils';
import { ArrowPathIcon } from '@heroicons/react/24/outline';

const MovieCard = ({ movie, settings }) => {
  const posterUrl = getImageUrl(movie.poster_path);
  
  // 修复安全模式模糊效果不起作用的问题
  // 1. 直接检查值是否等于true或字符串"true"
  const isSecureMode = settings.secure_mode === true || settings.secure_mode === "true";
  
  const imageClassName = `w-full h-full object-cover transition-all duration-300 ${
    isSecureMode ? 'blur-lg group-hover:blur-none' : ''
  }`;
  
  // 根据设置动态调整宽高比 - 修复2.12:3比例不生效的问题
  // 确保字符串值比较正确
  const isCustomRatio = String(settings.homepage_aspect_ratio) === '2.12:3';
  
  const aspectRatioStyle = {
    aspectRatio: isCustomRatio ? '2.12/3' : '2/3'
  };
  
  return (
    <div className="bg-[var(--color-secondary-bg)] rounded-lg overflow-hidden shadow-lg transform hover:-translate-y-1 transition-transform duration-300 group">
      <div className="relative w-full bg-[var(--color-secondary-bg)] overflow-hidden" style={aspectRatioStyle}>
        <img 
            src={posterUrl} 
            alt={`Poster for ${movie.bangou}`} 
            className={imageClassName} 
            loading="lazy"
        />
      </div>
      <div className="p-3">
        <h3 className="text-md font-bold text-[var(--color-primary-text)] truncate group-hover:text-[var(--color-primary-accent)]" title={movie.bangou}>{movie.bangou}</h3>
        <p className="text-sm text-[var(--color-primary-text)] truncate" title={movie.title}>{movie.title}</p>
        <p className="text-xs text-[var(--color-secondary-text)] truncate mt-1" title={movie.item_path}>{movie.item_path}</p>
      </div>
    </div>
  );
};

function HomePage() {
  const [movies, setMovies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [settings, setSettings] = useState({});
  const [refreshingCache, setRefreshingCache] = useState(false);

  const fetchAllData = async () => {
    setLoading(true);
    try {
      const [settingsRes, moviesRes] = await Promise.all([
        axios.get('/api/settings'),
        axios.get('/api/latest-items')
      ]);
      
      // 确保获取正确的settings格式，兼容新旧API
      const settingsData = settingsRes.data.settings || settingsRes.data;
      
      // 安全模式的特别处理
      settingsData.secure_mode = 
        settingsData.secure_mode === true || 
        settingsData.secure_mode === "true" ||
        settingsData.secure_mode === "yes" ||
        settingsData.secure_mode === 1;
      
      console.log('获取到的设置:', settingsData); // 添加日志，用于调试
      setSettings(settingsData);
      setMovies(moviesRes.data);
    } catch (error) {
      console.error("获取主页数据失败:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData();
    
    // 定时刷新数据，每5分钟刷新一次
    const refreshInterval = setInterval(fetchAllData, 5 * 60 * 1000);
    
    // 清理定时器
    return () => clearInterval(refreshInterval);
  }, []);

  // 刷新封面缓存
  const handleRefreshCache = async () => {
    if (refreshingCache) return;
    
    setRefreshingCache(true);
    try {
      const response = await axios.post('/api/cover-cache/refresh');
      if (response.data.success) {
        alert(`封面缓存已刷新: ${response.data.message}`);
        // 重新加载数据以显示最新的缓存
        await fetchAllData();
      } else {
        throw new Error(response.data.message || '刷新失败');
      }
    } catch (error) {
      alert(`刷新封面缓存失败: ${error.message}`);
      console.error('刷新封面缓存错误:', error);
    } finally {
      setRefreshingCache(false);
    }
  };

  const sizeClasses = {
    small: 'grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 xl:grid-cols-10 2xl:grid-cols-12',
    medium: 'grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-8',
    large: 'grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6',
  };
  const gridClassName = `grid ${sizeClasses[settings.cover_size] || sizeClasses.medium} gap-6`;

  if (loading) {
    return <div className="text-center text-xl text-[var(--color-secondary-text)]">加载中...</div>;
  }
  
  // 显示当前设置状态，用于调试
  console.log('渲染使用的设置:', settings);
  console.log('比例设置值:', settings.homepage_aspect_ratio, '类型:', typeof settings.homepage_aspect_ratio);
  console.log('安全模式设置值:', settings.secure_mode, '类型:', typeof settings.secure_mode);
  
  // 检查是否启用了安全模式
  const isSecureMode = settings.secure_mode === true || settings.secure_mode === "true";
  
  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-4xl font-bold text-[var(--color-primary-text)]">
          最新入库
          {isSecureMode && <span className="ml-2 text-sm bg-yellow-500 text-white px-2 py-1 rounded">安全模式已开启</span>}
        </h1>
        
        {/* 添加刷新封面缓存按钮 */}
        <button
          onClick={handleRefreshCache}
          disabled={refreshingCache}
          className="flex items-center gap-2 bg-[var(--color-primary-accent)] hover:bg-opacity-80 text-white px-4 py-2 rounded-md text-sm disabled:opacity-50"
          title="刷新封面缓存"
        >
          <ArrowPathIcon className={`h-5 w-5 ${refreshingCache ? 'animate-spin' : ''}`} />
          {refreshingCache ? '刷新中...' : '刷新封面缓存'}
        </button>
      </div>
      
      {movies.length === 0 ? (
        <div className="text-center text-xl text-[var(--color-secondary-text)] mt-10">
            没有找到"高画质"的影片。
            <p className="text-sm mt-2">请检查 Emby Webhook 是否正常工作，或在"高清替换"页面处理低画质任务。</p>
        </div>
      ) : (
        <div className={gridClassName}>
          {movies.map(movie => (
            <MovieCard key={movie.id} movie={movie} settings={settings} />
          ))}
        </div>
      )}
    </div>
  );
}

export default HomePage;
