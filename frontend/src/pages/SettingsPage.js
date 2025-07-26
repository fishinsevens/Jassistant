import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { CheckCircleIcon, PaperAirplaneIcon, InformationCircleIcon, ArrowPathIcon } from '@heroicons/react/24/solid';

const WATERMARK_TARGETS = [ { id: 'poster', name: '封面 (Poster)' }, { id: 'thumb', name: '缩略图 (Thumb)' }, { id: 'fanart', name: '背景图 (Fanart)' }, ];

function SettingsPage() {
  const [settings, setSettings] = useState({});
  const [restartRequiredSettings, setRestartRequiredSettings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showSuccess, setShowSuccess] = useState(false);
  const [restartNeeded, setRestartNeeded] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [testStatus, setTestStatus] = useState(null); // null, 'success', 'error'
  const [testMessage, setTestMessage] = useState('');
  const [activeTab, setActiveTab] = useState('instant'); // 'instant' 或 'restart'

  useEffect(() => {
    axios.get('/api/settings')
      .then(res => {
        // 新的API响应格式包含settings和restart_required_settings
        setSettings(res.data.settings || res.data); // 兼容旧版API
        setRestartRequiredSettings(res.data.restart_required_settings || []);
      })
      .catch(err => console.error("加载设置失败", err))
      .finally(() => setLoading(false));
  }, []);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setSettings(prev => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
  };
  
  const handleWatermarkTargetChange = (e) => {
    const { name, checked } = e.target;
    setSettings(prev => {
      const currentTargets = prev.watermark_targets || [];
      if (checked) return { ...prev, watermark_targets: [...currentTargets, name] };
      return { ...prev, watermark_targets: currentTargets.filter(t => t !== name) };
    });
  };

  const handleSave = () => {
    axios.post('/api/settings', settings)
      .then(response => { 
          setShowSuccess(true); 
          setTimeout(() => setShowSuccess(false), 2000);
          
          // 检查响应中的重启需求
          const needsRestart = response.data.restart_needed;
          setRestartNeeded(needsRestart);
          
          if (needsRestart) {
            // 如果需要重启，显示更详细的提示
            alert("您修改了需要重启容器才能生效的设置。请在方便的时候重启容器以应用这些更改。");
          }
      })
      .catch(err => alert("保存失败: " + err.response?.data?.message));
  };

  // 检查设置项是否需要重启生效
  const isRestartRequired = (settingKey) => {
    return restartRequiredSettings.includes(settingKey);
  };

  // 为需要重启的设置项添加重启图标
  const renderRestartIcon = (settingKey) => {
    if (isRestartRequired(settingKey)) {
      return (
        <div className="ml-2 inline-flex items-center text-amber-500" title="此设置需要重启容器才能生效">
          <ArrowPathIcon className="h-4 w-4" />
        </div>
      );
    }
    return null;
  };

  const handleTestNotification = () => {
    setIsTesting(true);
    setTestStatus(null);
    setTestMessage('');
    
    axios.post('/api/test-notification')
      .then(res => {
        setTestStatus('success');
        setTestMessage(res.data.message);
      })
      .catch(err => {
        setTestStatus('error');
        // 提取详细的错误信息
        let errorMsg = '测试失败';
        if (err.response && err.response.data && err.response.data.message) {
          errorMsg = err.response.data.message;
        } else if (err.message) {
          errorMsg = err.message;
        }
        setTestMessage(errorMsg);
      })
      .finally(() => setIsTesting(false));
  };

  const updateLogLevel = (level) => {
    axios.post('/api/update-log-level', { log_level: level })
      .then(res => {
        alert(res.data.message);
        // 更新本地设置
        setSettings(prev => ({ ...prev, log_level: level }));
      })
      .catch(err => alert(`更新日志级别失败: ${err.response?.data?.message || err.message}`));
  };
  
  const handleRestartContainer = () => {
    if (window.confirm('确定要重启容器吗？这将短暂中断服务。')) {
      axios.post('/api/restart-container')
        .then(res => {
          alert('容器正在重启，请稍后刷新页面。');
        })
        .catch(err => {
          alert(`重启容器失败: ${err.response?.data?.message || err.message}`);
        });
    }
  };

  if (loading) return <p className="text-[var(--color-secondary-text)]">加载设置中...</p>;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-4xl font-bold text-[var(--color-primary-text)]">系统设置</h1>
        <div className="flex items-center gap-4">
          <button 
            onClick={handleRestartContainer}
            className="flex items-center gap-2 bg-amber-500 text-white px-3 py-1 rounded-md hover:bg-amber-600 transition-colors"
          >
            <ArrowPathIcon className="h-4 w-4" />
            重启容器
          </button>
          <div className="flex items-center gap-1 text-sm text-[var(--color-secondary-text)]">
            <InformationCircleIcon className="h-5 w-5" />
            <span>版本: {settings.version || 'v0.0.1'}</span>
          </div>
        </div>
      </div>
      
      {restartNeeded && (
        <div className="mb-6 p-4 bg-amber-100 border-l-4 border-amber-500 text-amber-700 rounded">
          <div className="flex items-center">
            <ArrowPathIcon className="h-6 w-6 mr-2" />
            <div>
              <p className="font-bold">需要重启容器</p>
              <p>您修改了需要重启才能生效的设置项。请点击右上角的"重启容器"按钮应用这些更改。</p>
            </div>
          </div>
        </div>
      )}
      
      {/* 设置分类标签 */}
      <div className="flex mb-6 border-b border-[var(--color-border)]">
        <button 
          onClick={() => setActiveTab('instant')}
          className={`py-2 px-4 font-medium text-lg ${activeTab === 'instant' 
            ? 'text-[var(--color-primary-accent)] border-b-2 border-[var(--color-primary-accent)]' 
            : 'text-[var(--color-secondary-text)] hover:text-[var(--color-primary-text)]'}`}
        >
          即时生效设置
        </button>
        <button 
          onClick={() => setActiveTab('restart')}
          className={`py-2 px-4 font-medium text-lg flex items-center ${activeTab === 'restart' 
            ? 'text-[var(--color-primary-accent)] border-b-2 border-[var(--color-primary-accent)]' 
            : 'text-[var(--color-secondary-text)] hover:text-[var(--color-primary-text)]'}`}
        >
          需重启设置
          {restartNeeded && <span className="ml-2 bg-amber-500 text-white text-xs px-2 py-1 rounded-full">已修改</span>}
        </button>
      </div>
      
      <div className="bg-[var(--color-secondary-bg)] p-6 rounded-lg max-w-2xl space-y-8">
        {activeTab === 'instant' && (
          <>
            <fieldset className="space-y-4">
              <legend className="text-xl font-semibold text-[var(--color-primary-accent)] border-b border-[var(--color-border)] pb-2 mb-4">主页显示</legend>
              <div>
                <label htmlFor="latest_movies_count" className="block text-lg font-medium text-[var(--color-primary-text)]">最新入库显示数量</label>
                <input type="number" name="latest_movies_count" id="latest_movies_count" value={settings.latest_movies_count || 24} onChange={handleChange} className="input-field mt-1" />
              </div>
              <div>
                <label htmlFor="cover_size" className="block text-lg font-medium text-[var(--color-primary-text)]">封面显示大小</label>
                <select name="cover_size" id="cover_size" value={settings.cover_size || 'medium'} onChange={handleChange} className="input-field mt-1">
                  <option value="small">小</option>
                  <option value="medium">中</option>
                  <option value="large">大</option>
                </select>
              </div>
              <div>
                <label htmlFor="homepage_aspect_ratio" className="block text-lg font-medium text-[var(--color-primary-text)]">主页封面显示比例</label>
                <select name="homepage_aspect_ratio" id="homepage_aspect_ratio" value={settings.homepage_aspect_ratio || '2:3'} onChange={handleChange} className="input-field mt-1">
                  <option value="2:3">2:3 (Emby 默认)</option>
                  <option value="2.12:3">2.12:3 (封面默认)</option>
                </select>
              </div>
              <div className="flex items-center">
                <input type="checkbox" name="secure_mode" id="secure_mode" checked={settings.secure_mode || false} onChange={handleChange} className="h-5 w-5 rounded bg-[var(--color-secondary-bg)] border-[var(--color-border)] text-[var(--color-primary-accent)] focus:ring-[var(--color-primary-accent)]" />
                <label htmlFor="secure_mode" className="ml-3 text-lg font-medium text-[var(--color-primary-text)]">安全模式 (模糊显示主页图片)</label>
              </div>
              <div className="flex items-center">
                <input type="checkbox" name="use_cover_cache" id="use_cover_cache" checked={settings.use_cover_cache !== false} onChange={handleChange} className="h-5 w-5 rounded bg-[var(--color-secondary-bg)] border-[var(--color-border)] text-[var(--color-primary-accent)] focus:ring-[var(--color-primary-accent)]" />
                <label htmlFor="use_cover_cache" className="ml-3 text-lg font-medium text-[var(--color-primary-text)]">启用封面缓存 (减少读取媒体库)</label>
              </div>
              <div>
                <label htmlFor="cover_cache_dir" className="block text-lg font-medium text-[var(--color-primary-text)]">封面缓存目录</label>
                <input type="text" name="cover_cache_dir" id="cover_cache_dir" value={settings.cover_cache_dir || 'cover_cache'} onChange={handleChange} className="input-field mt-1" />
                <p className="text-sm text-[var(--color-secondary-text)] mt-1">相对于容器内部的路径，默认为 cover_cache</p>
              </div>
            </fieldset>
            
            <fieldset className="space-y-4">
              <legend className="text-xl font-semibold text-[var(--color-primary-accent)] border-b border-[var(--color-border)] pb-2 mb-4">水印处理</legend>
              <div>
                <h4 className="text-lg font-medium text-[var(--color-primary-text)] mb-2">应用目标</h4>
                {WATERMARK_TARGETS.map((target) => (
                    <div key={target.id} className="flex items-center"><input id={target.id} name={target.id} type="checkbox" checked={settings.watermark_targets?.includes(target.id)} onChange={handleWatermarkTargetChange} className="h-5 w-5 rounded bg-[var(--color-secondary-bg)] border-[var(--color-border)] text-[var(--color-primary-accent)] focus:ring-[var(--color-primary-accent)]" /><label htmlFor={target.id} className="ml-3 text-lg text-[var(--color-primary-text)]">{target.name}</label></div>
                ))}
              </div>
              <div>
                <label htmlFor="watermark_scale_ratio" className="block text-lg font-medium text-[var(--color-primary-text)]">缩放倍率 (图片高/水印高)</label>
                <input type="number" name="watermark_scale_ratio" value={settings.watermark_scale_ratio || 12} onChange={handleChange} className="input-field mt-1" />
              </div>
              <div>
                <label htmlFor="watermark_horizontal_offset" className="block text-lg font-medium text-[var(--color-primary-text)]">横向边距 (px)</label>
                <input type="number" name="watermark_horizontal_offset" value={settings.watermark_horizontal_offset || 12} onChange={handleChange} className="input-field mt-1" />
              </div>
              <div>
                <label htmlFor="watermark_vertical_offset" className="block text-lg font-medium text-[var(--color-primary-text)]">纵向边距 (px)</label>
                <input type="number" name="watermark_vertical_offset" value={settings.watermark_vertical_offset || 6} onChange={handleChange} className="input-field mt-1" />
              </div>
              <div>
                <label htmlFor="watermark_spacing" className="block text-lg font-medium text-[var(--color-primary-text)]">水印间距 (px)</label>
                <input type="number" name="watermark_spacing" value={settings.watermark_spacing || 6} onChange={handleChange} className="input-field mt-1" />
              </div>
            </fieldset>
            
            <fieldset className="space-y-4">
              <legend className="text-xl font-semibold text-[var(--color-primary-accent)] border-b border-[var(--color-border)] pb-2 mb-4">图片裁剪与质量判断</legend>
              <div>
                <label htmlFor="poster_crop_ratio" className="block text-lg font-medium text-[var(--color-primary-text)]">海报裁剪比例 (高/宽)</label>
                <p className="text-sm text-[var(--color-secondary-text)] mb-1">默认值为 1.415</p>
                <input type="number" step="0.001" name="poster_crop_ratio" value={settings.poster_crop_ratio || 1.415} onChange={handleChange} className="input-field mt-1" />
              </div>
              
              <div>
                <label htmlFor="high_quality_min_height" className="block text-lg font-medium text-[var(--color-primary-text)]">高画质最小高度 (像素)</label>
                <input type="number" name="high_quality_min_height" value={settings.high_quality_min_height || 800} onChange={handleChange} className="input-field mt-1" />
              </div>
              
              <div>
                <label htmlFor="high_quality_min_width" className="block text-lg font-medium text-[var(--color-primary-text)]">高画质最小宽度 (像素)</label>
                <input type="number" name="high_quality_min_width" value={settings.high_quality_min_width || 450} onChange={handleChange} className="input-field mt-1" />
              </div>
              
              <div>
                <label htmlFor="high_quality_min_size_kb" className="block text-lg font-medium text-[var(--color-primary-text)]">高画质最小文件大小 (KB)</label>
                <input type="number" name="high_quality_min_size_kb" value={settings.high_quality_min_size_kb || 50} onChange={handleChange} className="input-field mt-1" />
              </div>
            </fieldset>
            
            <fieldset className="space-y-4">
              <legend className="text-xl font-semibold text-[var(--color-primary-accent)] border-b border-[var(--color-border)] pb-2 mb-4">通知设置</legend>
              <div>
                <label htmlFor="notification_type" className="block text-lg font-medium text-[var(--color-primary-text)]">通知方式</label>
                <select name="notification_type" id="notification_type" value={settings.notification_type || 'custom'} onChange={handleChange} className="input-field mt-1">
                  <option value="custom">自定义通知</option>
                  <option value="telegram">Telegram机器人</option>
                </select>
              </div>
              
              {settings.notification_type === 'custom' && (
                <>
                  <div>
                    <label htmlFor="notification_api_url" className="block text-lg font-medium text-[var(--color-primary-text)]">接口地址</label>
                    <input type="text" name="notification_api_url" value={settings.notification_api_url || ''} onChange={handleChange} className="input-field mt-1" />
                  </div>
                  <div>
                    <label htmlFor="notification_route_id" className="block text-lg font-medium text-[var(--color-primary-text)]">Route ID</label>
                    <input type="text" name="notification_route_id" value={settings.notification_route_id || ''} onChange={handleChange} className="input-field mt-1" />
                  </div>
                </>
              )}
              
              {settings.notification_type === 'telegram' && (
                <>
                  <div>
                    <label htmlFor="telegram_bot_token" className="block text-lg font-medium text-[var(--color-primary-text)]">Bot Token</label>
                    <input type="text" name="telegram_bot_token" value={settings.telegram_bot_token || ''} onChange={handleChange} className="input-field mt-1" />
                    <p className="text-sm text-[var(--color-secondary-text)] mt-1">从 BotFather 获取的机器人Token</p>
                  </div>
                  <div>
                    <label htmlFor="telegram_chat_id" className="block text-lg font-medium text-[var(--color-primary-text)]">Chat ID</label>
                    <input type="text" name="telegram_chat_id" value={settings.telegram_chat_id || ''} onChange={handleChange} className="input-field mt-1" />
                    <p className="text-sm text-[var(--color-secondary-text)] mt-1">接收通知的用户ID或群组ID</p>
                  </div>
                  
                  <div className="mt-4">
                    <label htmlFor="telegram_random_image_api" className="block text-lg font-medium text-[var(--color-primary-text)]">随机图片API</label>
                    <input type="text" name="telegram_random_image_api" value={settings.telegram_random_image_api || ''} onChange={handleChange} className="input-field mt-1" placeholder="输入随机图片API地址" />
                    <p className="text-sm text-[var(--color-secondary-text)] mt-1">随机图片API的URL，留空则不发送图片</p>
                  </div>
                </>
              )}
              
              <div>
                <button 
                  onClick={handleTestNotification} 
                  disabled={isTesting} 
                  className="flex items-center justify-center gap-2 bg-[var(--color-sidebar-bg)] text-[var(--color-primary-text)] px-4 py-2 rounded-md text-sm font-semibold hover:bg-opacity-80 transition-colors disabled:opacity-50">
                  <PaperAirplaneIcon className="h-5 w-5"/>
                  {isTesting ? '发送中...' : '发送测试通知'}
                </button>
                {testStatus === 'success' && (
                  <div className="mt-2 text-sm text-green-500">
                    {testMessage || '通知发送成功，请检查您的通知服务。'}
                  </div>
                )}
                {testStatus === 'error' && (
                  <div className="mt-2 text-sm text-red-500">
                    <p><strong>错误：</strong> {testMessage}</p>
                    <p className="mt-1">可能的解决方法:</p>
                    <ul className="list-disc pl-5 mt-1">
                      <li>检查接口地址或Token是否正确</li>
                      <li>确认目标服务器是否可访问</li>
                      <li>尝试增加超时时间</li>
                      <li>查看系统日志获取更多信息</li>
                    </ul>
                  </div>
                )}
              </div>
            </fieldset>
          </>
        )}
        
        {activeTab === 'restart' && (
          <>
            <fieldset className="space-y-4">
              <legend className="text-xl font-semibold text-[var(--color-primary-accent)] border-b border-[var(--color-border)] pb-2 mb-4">
                系统设置
                <span className="text-amber-500 ml-2 text-sm font-normal">需要重启容器才能生效</span>
              </legend>
              
              <div>
                <label htmlFor="media_root" className="block text-lg font-medium text-[var(--color-primary-text)] flex items-center">
                  媒体根路径
                  <ArrowPathIcon className="h-4 w-4 ml-2 text-amber-500" />
                </label>
                <input type="text" name="media_root" id="media_root" value={settings.media_root || '/weiam'} onChange={handleChange} className="input-field mt-1" />
                <p className="text-sm text-[var(--color-secondary-text)] mt-1">必须与Docker容器内的挂载路径一致</p>
              </div>
              
              <div>
                <label htmlFor="log_level" className="block text-lg font-medium text-[var(--color-primary-text)] flex items-center">
                  日志级别
                  <ArrowPathIcon className="h-4 w-4 ml-2 text-amber-500" />
                </label>
                <div className="mt-2 flex flex-wrap gap-2">
                  {['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'].map(level => (
                    <button
                      key={level}
                      onClick={() => updateLogLevel(level)}
                      className={`px-4 py-2 rounded-md ${settings.log_level === level 
                        ? 'bg-[var(--color-primary-accent)] text-white font-bold' 
                        : 'bg-[var(--color-sidebar-bg)] text-[var(--color-primary-text)]'}`}
                    >
                      {level}
                    </button>
                  ))}
                </div>
                
                <p className="mt-2 text-sm text-[var(--color-secondary-text)]">
                  当前日志级别: <span className="font-bold">{settings.log_level || 'INFO'}</span>
                  <br/>
                  <span className="text-amber-500">注意：更改日志级别可立即生效，但需要重启容器才能完全应用于所有组件</span>
                </p>
              </div>
            </fieldset>
            
            <fieldset className="space-y-4">
              <legend className="text-xl font-semibold text-[var(--color-primary-accent)] border-b border-[var(--color-border)] pb-2 mb-4">
                通知计划
                <span className="text-amber-500 ml-2 text-sm font-normal">需要重启容器才能生效</span>
              </legend>
              
              <div className="flex items-center">
                <input type="checkbox" name="notification_enabled" id="notification_enabled" checked={settings.notification_enabled || false} onChange={handleChange} className="h-5 w-5 rounded bg-[var(--color-secondary-bg)] border-[var(--color-border)] text-[var(--color-primary-accent)] focus:ring-[var(--color-primary-accent)]" />
                <label htmlFor="notification_enabled" className="ml-3 text-lg font-medium text-[var(--color-primary-text)] flex items-center">
                  启用每日入库通知
                  <ArrowPathIcon className="h-4 w-4 ml-2 text-amber-500" />
                </label>
              </div>
              
              <div>
                <label htmlFor="notification_time" className="block text-lg font-medium text-[var(--color-primary-text)] flex items-center">
                  通知时间
                  <ArrowPathIcon className="h-4 w-4 ml-2 text-amber-500" />
                </label>
                <input type="time" name="notification_time" value={settings.notification_time || '09:00'} onChange={handleChange} className="input-field mt-1" />
                <p className="text-sm text-amber-500 mt-1">修改通知时间后需要重启容器，才能按新时间发送通知</p>
              </div>
            </fieldset>
          </>
        )}
        
        <div className="pt-4 border-t border-[var(--color-border)]">
          <div className="flex items-center justify-between">
            <div>
              <button onClick={handleSave} className="bg-[var(--color-primary-accent)] hover:bg-opacity-80 text-white font-bold py-2 px-4 rounded-md inline-flex items-center transition-colors">保存设置</button>
              {showSuccess && <span className="inline-flex items-center gap-2 text-[var(--color-secondary-accent)] ml-4"><CheckCircleIcon className="h-6 w-6" /> 保存成功!</span>}
            </div>
            
            {restartNeeded && (
              <button 
                onClick={handleRestartContainer}
                className="bg-amber-500 hover:bg-amber-600 text-white font-bold py-2 px-4 rounded-md inline-flex items-center transition-colors"
              >
                <ArrowPathIcon className="h-5 w-5 mr-2" />
                应用更改并重启
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default SettingsPage;
