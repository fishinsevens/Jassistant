import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { ArrowPathIcon, CheckCircleIcon, XCircleIcon, SparklesIcon, ChevronDownIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline';
import ImageProcessorModal from '../components/ImageProcessorModal';
import { getImageUrl } from '../utils'; // 优化：从 utils 导入

import { useLinkVerification } from '../hooks/useLinkVerification';

const StatusBadge = ({ status }) => {
  const statusStyles = {
    '低画质': 'bg-yellow-400 text-yellow-900',
    '高画质': 'bg-green-400 text-green-900',
    '未知': 'bg-gray-400 text-gray-900',
    'NoHD': 'bg-gray-600 text-gray-100'
  };
  return ( <span className={`px-2 py-1 text-xs font-bold rounded-full ${statusStyles[status] || 'bg-gray-500'}`}>{status}</span> );
};

const DmmLink = ({ linkInfo, children, verificationStatus, showStatus = true }) => {
  // verificationStatus: 'pending' | 'valid' | 'invalid' | undefined
  // showStatus: 是否显示验证状态图标
  const status = verificationStatus || (linkInfo.valid !== undefined ? (linkInfo.valid ? 'valid' : 'invalid') : 'pending');

  const getStatusIcon = () => {
    if (!showStatus) return null; // DMM链接不显示状态图标

    switch (status) {
      case 'pending':
        return <ArrowPathIcon className="h-4 w-4 animate-spin text-gray-400" />;
      case 'valid':
        return <CheckCircleIcon className="h-4 w-4 text-[var(--color-secondary-accent)]" />;
      case 'invalid':
        return <XCircleIcon className="h-4 w-4 text-[var(--color-danger)]" />;
      default:
        return <ArrowPathIcon className="h-4 w-4 animate-spin text-gray-400" />;
    }
  };

  const getStatusClass = () => {
    if (!showStatus) {
      return 'text-blue-400 hover:text-blue-300'; // DMM链接始终可点击
    }

    switch (status) {
      case 'pending':
        return 'text-gray-400';
      case 'valid':
        return 'text-blue-400 hover:text-blue-300';
      case 'invalid':
        return 'text-blue-400 hover:text-blue-300'; // 无效链接也可点击，只是显示不同图标
      default:
        return 'text-gray-400';
    }
  };

  return (
    <a
      href={linkInfo.url}
      target="_blank"
      rel="noopener noreferrer"
      className={`flex items-center gap-1 text-sm transition-colors ${getStatusClass()}`}
    >
      {children} {getStatusIcon()}
    </a>
  );
};

function HdReplacePage() {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [dmmInfo, setDmmInfo] = useState({});
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalData, setModalData] = useState(null);
  // 手动输入番号相关状态，改为每个任务独立管理
  const [manualInputs, setManualInputs] = useState({});
  const [loadingManual, setLoadingManual] = useState({});
  // 使用链接验证Hook
  const {
    linkVerificationStatus,
    verifyLinksWithTaskId: verifyLinks,
    refreshLinkVerificationWithTaskId: refreshLinkVerification
  } = useLinkVerification();

  const fetchTasks = useCallback((pageNum) => {
    setLoading(true);
    axios.get(`/api/low-quality-items?page=${pageNum}`)
      .then(response => {
        const newTasks = response.data.items;
        setTasks(prevTasks => pageNum === 1 ? newTasks : [...prevTasks, ...newTasks]);
        setHasMore(response.data.has_more);
      })
      .catch(error => console.error("获取待办任务失败:", error))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { fetchTasks(1); }, [fetchTasks]);



  const handleSearchCid = (taskId, bangou) => {
    setDmmInfo(prev => ({ ...prev, [taskId]: { loading: true } }));
    axios.get(`/api/get-dmm-info?bangou=${bangou}`)
      .then(response => {
        const results = response.data.results;
        setDmmInfo(prev => ({ ...prev, [taskId]: { loading: false, data: results } }));
        // 自动触发链接验证
        verifyLinks(taskId, results);
      })
      .catch(error => setDmmInfo(prev => ({ ...prev, [taskId]: { loading: false, error: error.response?.data?.message || "查询失败" } })));
  };

  // 手动输入番号获取CID - 为每个任务单独处理
  const handleManualCidSearch = (taskId) => {
    const manualBangou = manualInputs[taskId] || '';
    if (!manualBangou.trim()) {
      alert('请输入有效的番号');
      return;
    }

    setLoadingManual(prev => ({ ...prev, [taskId]: true }));

    axios.get(`/api/get-manual-cid-info?bangou=${manualBangou.trim()}`)
      .then(response => {
        if (response.data.success && response.data.results?.length > 0) {
          const results = response.data.results;
          setDmmInfo(prev => ({
            ...prev,
            [taskId]: {
              loading: false,
              data: results,
              manualMode: true,
              bangou: manualBangou.trim()
            }
          }));
          // 自动触发链接验证
          verifyLinks(taskId, results);
        } else {
          setDmmInfo(prev => ({
            ...prev,
            [taskId]: {
              loading: false,
              error: '未找到匹配的结果',
              manualMode: true
            }
          }));
        }
      })
      .catch(error => {
        setDmmInfo(prev => ({
          ...prev,
          [taskId]: {
            loading: false,
            error: error.response?.data?.message || '查询失败',
            manualMode: true
          }
        }));
      })
      .finally(() => {
        setLoadingManual(prev => ({ ...prev, [taskId]: false }));
      });
  };

  const handleManualInputChange = (taskId, value) => {
    setManualInputs(prev => ({ ...prev, [taskId]: value }));
  };

  const handleSkip = (taskId) => {
    axios.post(`/api/skip-item/${taskId}`)
      .then(() => setTasks(prev => prev.filter(t => t.id !== taskId)))
      .catch(error => alert(`跳过失败: ${error.response?.data?.message}`));
  };

  const handleRefresh = (taskId) => {
    axios.post(`/api/refresh-item-images/${taskId}`)
      .then(res => {
        const updatedData = res.data.data;
        setTasks(prevTasks => {
          if (updatedData.poster_status !== '低画质' && updatedData.fanart_status !== '低画质') {
            return prevTasks.filter(t => t.id !== taskId);
          }
          return prevTasks.map(t => t.id === taskId ? { ...t, ...updatedData } : t);
        });
        alert("刷新成功！");
      })
      .catch(err => alert(`刷新失败: ${err.response?.data?.message}`));
  };

  const openImageProcessor = (task, imageUrl, imageType) => {
    setModalData({ item_id: task.id, image_url: imageUrl, image_type: imageType, bangou: task.bangou });
    setIsModalOpen(true);
  };

  return (
    <>
      <h1 className="text-4xl font-bold text-[var(--color-primary-text)] mb-6">高清替换</h1>
      <div className="space-y-4">
        {tasks.map(task => {
          const posterUrl = getImageUrl(task.poster_path, 'https://placehold.co/150x225/181828/94A1B2?text=No+Poster');
          const info = dmmInfo[task.id];
          const isLoadingManual = loadingManual[task.id];
          
          return (
            <div key={task.id} className="bg-[var(--color-secondary-bg)] rounded-lg p-4 flex flex-col md:flex-row gap-4">
              <div className="md:w-32 flex-shrink-0 self-center">
                <img 
                  src={posterUrl} 
                  alt={task.bangou} 
                  className="w-full h-auto aspect-[2/3] object-cover rounded-md" 
                  onError={(e) => {e.target.onerror = null; e.target.src="https://placehold.co/150x225/181828/94A1B2?text=No+Poster"}}
                />
              </div>
              <div className="flex-grow">
                <h3 className="text-xl font-bold text-[var(--color-primary-text)]">{task.bangou}</h3>
                <p className="text-xs text-[var(--color-secondary-text)] break-all mb-2">{task.item_path}</p>
                <div className="flex gap-2 items-center mb-3">海报: <StatusBadge status={task.poster_status} /> 壁纸: <StatusBadge status={task.fanart_status} /></div>
                
                <div className="flex flex-wrap gap-2 mb-2">
                  <button onClick={() => handleSearchCid(task.id, task.bangou)} disabled={info?.loading} className="bg-[var(--color-primary-accent)] hover:bg-opacity-80 text-white px-3 py-1 rounded-md text-sm inline-flex items-center gap-1">
                    {info?.loading && !info?.manualMode ? <ArrowPathIcon className="h-4 w-4 animate-spin" /> : <SparklesIcon className="h-4 w-4" />} 查询DMM
                  </button>
                  
                  {/* 添加手动输入番号区域 - 放在查询DMM按钮旁边 */}
                  <div className="inline-flex items-center gap-1">
                    <input
                      type="text"
                      value={manualInputs[task.id] || ''}
                      onChange={(e) => handleManualInputChange(task.id, e.target.value)}
                      placeholder="输入番号或CID..."
                      className="input-field py-1 text-sm w-28"
                      onKeyPress={(e) => e.key === 'Enter' && handleManualCidSearch(task.id)}
                    />
                    <button
                      onClick={() => handleManualCidSearch(task.id)}
                      disabled={isLoadingManual}
                      className="bg-[var(--color-secondary-accent)] hover:bg-opacity-80 text-white px-3 py-1 rounded-md text-sm inline-flex items-center gap-1"
                    >
                      {isLoadingManual ? <ArrowPathIcon className="h-4 w-4 animate-spin" /> : <MagnifyingGlassIcon className="h-4 w-4" />}
                    </button>
                  </div>
                  
                  <button onClick={() => handleRefresh(task.id)} className="bg-blue-600 hover:bg-blue-500 text-white px-3 py-1 rounded-md text-sm inline-flex items-center gap-1">
                    <ArrowPathIcon className="h-4 w-4" /> 刷新
                  </button>
                  <button onClick={() => handleSkip(task.id)} className="bg-gray-600 hover:bg-gray-500 text-white px-3 py-1 rounded-md text-sm">跳过</button>
                </div>
                
                {/* 移除单独的手动输入番号区域 */}
                
                {info && (
                  <div className="mt-2 bg-[var(--color-sidebar-bg)] p-3 rounded-md">
                    {info.loading && !info.manualMode && <p>查询中...</p>}
                    {info.error && <p className="text-[var(--color-danger)]">{info.error}</p>}
                    {info.data?.map((res, index) => {
                      const wallpaperStatus = linkVerificationStatus[`${task.id}-${index}-wallpaper`];
                      const coverStatus = linkVerificationStatus[`${task.id}-${index}-cover`];

                      return (
                        <div key={index} className="text-sm">
                          <p className="font-bold">CID: {res.cid} {info.manualMode && info.bangou && `(番号: ${info.bangou})`}</p>
                          <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1">
                            <DmmLink linkInfo={{url: `https://www.dmm.co.jp/digital/videoa/-/detail/=/cid=${res.cid}/`}} showStatus={false}>DMM链接</DmmLink>
                            <DmmLink linkInfo={res.wallpaper_url} verificationStatus={wallpaperStatus}>壁纸链接</DmmLink>
                            <DmmLink linkInfo={res.cover_url} verificationStatus={coverStatus}>封面链接</DmmLink>
                            <button
                              onClick={() => openImageProcessor(task, res.wallpaper_url.url, 'fanart')}
                              className="text-[var(--color-secondary-accent)] text-sm hover:underline"
                            >
                              处理壁纸
                            </button>
                            <button
                              onClick={() => openImageProcessor(task, res.cover_url.url, 'poster')}
                              className="text-[var(--color-secondary-accent)] text-sm hover:underline"
                            >
                              处理封面
                            </button>
                            <button
                              onClick={() => refreshLinkVerification(task.id, info.data)}
                              className="text-orange-400 text-sm hover:underline"
                              title="刷新链接验证状态"
                            >
                              🔄 刷新
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )
        })}
        {loading && <p className="text-center">加载中...</p>}
        {hasMore && !loading && (
          <button onClick={() => { setPage(p => p + 1); fetchTasks(page + 1); }} className="w-full bg-[var(--color-secondary-bg)] hover:bg-[var(--color-primary-accent)] py-2 rounded-md flex items-center justify-center gap-2">
            加载更多 <ChevronDownIcon className="h-5 w-5" />
          </button>
        )}
      </div>
      {isModalOpen && <ImageProcessorModal data={modalData} onClose={(processed) => { setIsModalOpen(false); if (processed) { setPage(1); fetchTasks(1); } }} />}
    </>
  );
}

export default HdReplacePage;
