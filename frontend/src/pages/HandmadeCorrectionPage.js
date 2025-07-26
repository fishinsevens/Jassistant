import { useState, useEffect, useCallback, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
    ArrowPathIcon,
    LinkIcon,
    PhotoIcon,
    CheckCircleIcon,
    ExclamationCircleIcon,
    ArrowUpTrayIcon,
    XCircleIcon
} from '@heroicons/react/24/outline';
import ImageProcessorModal from '../components/ImageProcessorModal';

import { useLinkVerification } from '../hooks/useLinkVerification';

const StatusBadge = ({ status }) => {
    const statusStyles = {
      '低画质': 'bg-yellow-400 text-yellow-900',
      '高画质': 'bg-green-400 text-green-900',
      '未知': 'bg-gray-400 text-gray-900',
      'NoHD': 'bg-gray-600 text-gray-100'
    };
    return ( <span className={`px-2 py-1 text-xs font-bold rounded-full ${statusStyles[status] || 'bg-gray-500'}`}>{status || 'N/A'}</span> );
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

const NfoEditor = ({ nfoData, onSave }) => {
    const [editorData, setEditorData] = useState({});
    const [saving, setSaving] = useState(false);
    const [saveResult, setSaveResult] = useState(null);
    
    useEffect(() => {
        const formattedData = { ...nfoData };
        for (const key of ['actors', 'genres', 'tags', 'sets']) {
            if (Array.isArray(formattedData[key])) {
                formattedData[key] = formattedData[key].join(', ');
            }
        }
        setEditorData(formattedData || {});
    }, [nfoData]);
    
    if (!nfoData) return null;
    
    const handleChange = (e) => {
        const { name, value } = e.target;
        setEditorData(prev => ({ ...prev, [name]: value }));
    };
    
    const handleSave = async () => {
        setSaving(true);
        setSaveResult(null);
        
        try {
            const dataToSave = { ...editorData };
            for (const key of ['actors', 'genres', 'tags', 'sets']) {
                if (typeof dataToSave[key] === 'string') {
                    dataToSave[key] = dataToSave[key].split(',').map(s => s.trim()).filter(Boolean);
                }
            }
            
            const result = await onSave(dataToSave);
            setSaveResult({ success: true, message: result.message || '保存成功' });
        } catch (error) {
            setSaveResult({ 
                success: false, 
                message: error.response?.data?.message || error.message || '保存失败'
            });
        } finally {
            setSaving(false);
            // 3秒后清除保存结果
            setTimeout(() => setSaveResult(null), 3000);
        }
    };
    
    return (
        <div className="bg-[var(--color-sidebar-bg)] p-4 rounded-lg mt-6">
            <h3 className="text-xl font-bold text-[var(--color-primary-text)] mb-4">NFO 编辑</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div className="flex flex-col">
                    <label className="mb-1 text-[var(--color-secondary-text)]">番号 (Num)</label>
                    <input 
                        name="num" 
                        value={editorData.num || ''} 
                        onChange={handleChange} 
                        placeholder="番号" 
                        className="input-field"
                    />
                </div>
                <div className="flex flex-col md:col-span-2">
                    <label className="mb-1 text-[var(--color-secondary-text)]">标语/短语 (Tagline)</label>
                    <input
                        name="tagline" 
                        value={editorData.tagline || ''} 
                        onChange={handleChange} 
                        placeholder="简短描述或口号" 
                        className="input-field"
                    />
                </div>
                <div className="flex flex-col">
                    <label className="mb-1 text-[var(--color-secondary-text)]">片名 (Title)</label>
                    <input 
                        name="title" 
                        value={editorData.title || ''} 
                        onChange={handleChange} 
                        placeholder="片名" 
                        className="input-field"
                    />
                </div>
                <div className="flex flex-col">
                    <label className="mb-1 text-[var(--color-secondary-text)]">原始片名 (Original Title)</label>
                    <input 
                        name="originaltitle" 
                        value={editorData.originaltitle || ''} 
                        onChange={handleChange} 
                        placeholder="原始片名" 
                        className="input-field"
                    />
                </div>
                <div className="flex flex-col md:col-span-2">
                    <label className="mb-1 text-[var(--color-secondary-text)]">剧情描述 (Plot)</label>
                    <textarea 
                        name="plot" 
                        value={editorData.plot || ''} 
                        onChange={handleChange} 
                        placeholder="剧情描述" 
                        className="input-field h-24"
                    />
                </div>
                <div className="flex flex-col md:col-span-2">
                    <label className="mb-1 text-[var(--color-secondary-text)]">原始剧情 (Original Plot)</label>
                    <textarea 
                        name="originalplot" 
                        value={editorData.originalplot || ''} 
                        onChange={handleChange} 
                        placeholder="原始剧情" 
                        className="input-field h-24"
                    />
                </div>
                <div className="flex flex-col">
                    <label className="mb-1 text-[var(--color-secondary-text)]">年份 (Year)</label>
                    <input 
                        name="year" 
                        value={editorData.year || ''} 
                        onChange={handleChange} 
                        placeholder="年份" 
                        className="input-field"
                    />
                </div>
                <div className="flex flex-col">
                    <label className="mb-1 text-[var(--color-secondary-text)]">发行日期 (Release Date)</label>
                    <input 
                        name="release_date" 
                        value={editorData.release_date || ''} 
                        onChange={handleChange} 
                        placeholder="发行日期 (YYYY-MM-DD)" 
                        className="input-field"
                    />
                </div>
                <div className="flex flex-col">
                    <label className="mb-1 text-[var(--color-secondary-text)]">制作商 (Studio)</label>
                    <input 
                        name="studio" 
                        value={editorData.studio || ''} 
                        onChange={handleChange} 
                        placeholder="制作商" 
                        className="input-field"
                    />
                </div>
                <div className="flex flex-col">
                    <label className="mb-1 text-[var(--color-secondary-text)]">发行商 (Label)</label>
                    <input 
                        name="label" 
                        value={editorData.label || ''} 
                        onChange={handleChange} 
                        placeholder="发行商" 
                        className="input-field"
                    />
                </div>
                <div className="flex flex-col">
                    <label className="mb-1 text-[var(--color-secondary-text)]">评分 (Rating)</label>
                    <input 
                        name="rating" 
                        value={editorData.rating || ''} 
                        onChange={handleChange} 
                        placeholder="评分" 
                        className="input-field"
                    />
                </div>
                <div className="flex flex-col">
                    <label className="mb-1 text-[var(--color-secondary-text)]">评级 (Critic Rating)</label>
                    <input 
                        name="criticrating" 
                        value={editorData.criticrating || ''} 
                        onChange={handleChange} 
                        placeholder="评级" 
                        className="input-field"
                    />
                </div>
                <div className="flex flex-col md:col-span-2">
                    <label className="mb-1 text-[var(--color-secondary-text)]">系列 (Sets)</label>
                    <input 
                        name="sets" 
                        value={editorData.sets || ''} 
                        onChange={handleChange} 
                        placeholder="系列 (逗号分隔)" 
                        className="input-field"
                    />
                </div>
                <div className="flex flex-col md:col-span-2">
                    <label className="mb-1 text-[var(--color-secondary-text)]">演员 (Actors)</label>
                    <textarea 
                        name="actors" 
                        value={editorData.actors || ''} 
                        onChange={handleChange} 
                        placeholder="演员 (逗号分隔)" 
                        className="input-field h-20"
                    />
                </div>
                <div className="flex flex-col md:col-span-2">
                    <label className="mb-1 text-[var(--color-secondary-text)]">类型 (Genres)</label>
                    <textarea 
                        name="genres" 
                        value={editorData.genres || ''} 
                        onChange={handleChange} 
                        placeholder="类型 (逗号分隔)" 
                        className="input-field h-20"
                    />
                </div>
                <div className="flex flex-col md:col-span-2">
                    <label className="mb-1 text-[var(--color-secondary-text)]">标签 (Tags)</label>
                    <textarea 
                        name="tags" 
                        value={editorData.tags || ''} 
                        onChange={handleChange} 
                        placeholder="标签 (逗号分隔)" 
                        className="input-field h-20"
                    />
                </div>
            </div>
            <div className="mt-6 flex items-center gap-4">
                <button 
                    onClick={handleSave} 
                    disabled={saving}
                    className="bg-[var(--color-primary-accent)] text-white px-6 py-2 rounded-md text-sm font-semibold hover:bg-opacity-80 flex items-center gap-2"
                >
                    {saving && <ArrowPathIcon className="h-4 w-4 animate-spin" />}
                    保存NFO
                </button>
                
                {saveResult && (
                    <div className={`flex items-center gap-2 ${saveResult.success ? 'text-green-500' : 'text-red-500'}`}>
                        {saveResult.success ? (
                            <CheckCircleIcon className="h-5 w-5" />
                        ) : (
                            <ExclamationCircleIcon className="h-5 w-5" />
                        )}
                        <span>{saveResult.message}</span>
                    </div>
                )}
            </div>
        </div>
    );
};

function HandmadeCorrectionPage() {
    const location = useLocation();
    const navigate = useNavigate();
    const [nfoPath] = useState(location.state?.nfoPath || '');
    const [loading, setLoading] = useState(true);
    const [pageData, setPageData] = useState(null);
    const [dmmInfo, setDmmInfo] = useState(null);
    const [loadingDmm, setLoadingDmm] = useState(false);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [modalData, setModalData] = useState(null);
    const fileInputRef = useRef(null);
    // 添加手动输入番号状态
    const [manualBangou, setManualBangou] = useState('');
    const [loadingManualCid, setLoadingManualCid] = useState(false);
    // 使用链接验证Hook
    const {
        linkVerificationStatus,
        verifyLinks,
        refreshLinkVerification
    } = useLinkVerification();

    const fetchData = useCallback(() => {
        if (nfoPath) {
            setLoading(true);
            axios.get(`/api/handmade/nfo-details?path=${encodeURIComponent(nfoPath)}`)
                .then(res => {
                    setPageData(res.data);
                    // 移除自动获取DMM信息
                })
                .catch(err => alert(`加载NFO详情失败: ${err.response?.data?.error || err.message}`))
                .finally(() => setLoading(false));
        }
    }, [nfoPath]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    // 验证单个链接


    const handleSearchDmm = (bangou) => {
        if (!bangou) {
            bangou = pageData?.nfo_data?.num;
            if (!bangou) {
                alert("没有可用的番号信息");
                return;
            }
        }
        setLoadingDmm(true);
        axios.get(`/api/get-dmm-info?bangou=${bangou}`)
            .then(res => {
                setDmmInfo(res.data);
                // 自动触发链接验证
                if (res.data.success && res.data.results) {
                    verifyLinks(res.data.results);
                }
            })
            .catch(err => setDmmInfo({ error: err.response?.data?.message || "查询失败" }))
            .finally(() => setLoadingDmm(false));
    };

    // 添加手动获取CID的函数
    const handleManualCidSearch = () => {
        if (!manualBangou || manualBangou.trim() === '') {
            alert("请输入有效的番号");
            return;
        }
        setLoadingManualCid(true);
        axios.get(`/api/get-manual-cid-info?bangou=${manualBangou.trim()}`)
            .then(res => {
                setDmmInfo(res.data);
                // 自动触发链接验证
                if (res.data.success && res.data.results) {
                    verifyLinks(res.data.results);
                }
            })
            .catch(err => setDmmInfo({ error: err.response?.data?.message || "获取CID失败" }))
            .finally(() => setLoadingManualCid(false));
    };

    const handleSaveNfo = async (newData) => {
        try {
            const response = await axios.post(`/api/handmade/save-nfo?path=${encodeURIComponent(nfoPath)}`, newData);
            fetchData(); // 刷新数据
            return response.data;
        } catch (error) {
            console.error("保存NFO失败:", error);
            throw error;
        }
    };

    const openImageProcessor = (imageUrl, imageType) => {
        setModalData({ 
            item_id: null,
            image_url: imageUrl, 
            image_type: imageType, 
            bangou: pageData?.nfo_data?.num,
            base_path: nfoPath.replace('.nfo', '')
        });
        setIsModalOpen(true);
    };
    
    // 添加处理本地图片上传的函数
    const handleFileChange = (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        // 创建临时URL用于ImageProcessor
        const tempUrl = URL.createObjectURL(file);
        setModalData({ 
            item_id: null,
            image_url: tempUrl, 
            image_type: 'fanart',  // 默认作为fanart处理，可以在模态框中修改
            bangou: pageData?.nfo_data?.num,
            base_path: nfoPath.replace('.nfo', ''),
            localFile: file  // 传递本地文件对象
        });
        setIsModalOpen(true);
    };
    
    const handleUploadClick = () => {
        fileInputRef.current?.click();
    };

    if (!nfoPath) {
        return (
            <div className="text-center">
                <h1 className="text-2xl font-bold">无效访问</h1>
                <p className="text-[var(--color-secondary-text)] mt-2">请从文件管理器中双击一个NFO文件来进入此页面。</p>
                <button onClick={() => navigate('/file-manager')} className="mt-4 bg-[var(--color-primary-accent)] text-white px-4 py-2 rounded-md">返回文件管理</button>
            </div>
        );
    }

    if (loading) {
        return <div className="text-center text-xl text-[var(--color-secondary-text)]">加载中...</div>;
    }
    
    if (!pageData) {
        return <div className="text-2xl font-bold text-center text-[var(--color-danger)]">加载数据失败。</div>;
    }

    const dmmResult = dmmInfo?.results?.[0];

    return (
        <div>
            <h1 className="text-4xl font-bold text-[var(--color-primary-text)] mb-2">手作修正</h1>
            <p className="text-sm text-[var(--color-secondary-text)] mb-6 break-all">{nfoPath}</p>
            
            <div className="bg-[var(--color-sidebar-bg)] p-3 rounded-lg flex items-center justify-between gap-4 mb-4">
                <div className="flex items-center gap-4">
                    {/* 添加上传本地图片按钮 */}
                    <button 
                        onClick={handleUploadClick}
                        className="flex items-center gap-1 bg-[var(--color-secondary-accent)] text-white px-3 py-1 rounded-md text-sm hover:opacity-80"
                    >
                        <ArrowUpTrayIcon className="h-4 w-4" /> 上传本地图片
                    </button>
                    <input 
                        type="file" 
                        ref={fileInputRef}
                        className="hidden" 
                        accept="image/*"
                        onChange={handleFileChange}
                    />
                    
                    {/* DMM信息部分 */}
                    {loadingDmm ? <ArrowPathIcon className="h-6 w-6 animate-spin"/> : (
                        dmmResult ? (
                            <>
                                <DmmLink linkInfo={{url: `https://www.dmm.co.jp/digital/videoa/-/detail/=/cid=${dmmResult.cid}/`}} showStatus={false}>
                                    <LinkIcon className="h-5 w-5"/> DMM链接
                                </DmmLink>
                                <DmmLink linkInfo={dmmResult.wallpaper_url} verificationStatus={linkVerificationStatus['0-wallpaper']}>
                                    壁纸链接
                                </DmmLink>
                                <DmmLink linkInfo={dmmResult.cover_url} verificationStatus={linkVerificationStatus['0-cover']}>
                                    封面链接
                                </DmmLink>
                                <button
                                    onClick={() => openImageProcessor(dmmResult.wallpaper_url.url, 'fanart')}
                                    title="处理壁纸"
                                    className="text-[var(--color-primary-text)] hover:text-[var(--color-primary-accent)]"
                                >
                                    <PhotoIcon className="h-6 w-6"/>
                                </button>
                                <button
                                    onClick={() => openImageProcessor(dmmResult.cover_url.url, 'poster')}
                                    title="处理封面"
                                    className="text-[var(--color-primary-text)] hover:text-[var(--color-primary-accent)]"
                                >
                                    <PhotoIcon className="h-6 w-6"/>
                                </button>
                                <button
                                    onClick={() => refreshLinkVerification(dmmInfo.results)}
                                    title="刷新链接验证状态"
                                    className="text-orange-400 hover:text-orange-300 text-sm"
                                >
                                    🔄
                                </button>
                            </>
                        ) : (
                            <>
                                <button 
                                    onClick={() => handleSearchDmm()}
                                    className="bg-[var(--color-primary-accent)] text-white px-3 py-1 rounded-md text-sm hover:opacity-80"
                                >
                                    获取DMM信息
                                </button>
                                {dmmInfo?.error && <span className="text-[var(--color-danger)] text-sm">{dmmInfo.error}</span>}
                            </>
                        )
                    )}

                    {/* 添加手动输入番号区域 */}
                    <div className="flex items-center gap-2 ml-4 border-l border-[var(--color-border)] pl-4">
                        <input
                            type="text"
                            value={manualBangou}
                            onChange={(e) => setManualBangou(e.target.value)}
                            placeholder="手动输入番号..."
                            className="input-field text-sm w-32"
                        />
                        <button
                            onClick={handleManualCidSearch}
                            disabled={loadingManualCid}
                            className="bg-[var(--color-secondary-accent)] text-white px-3 py-1 rounded-md text-sm hover:opacity-80 disabled:opacity-50"
                        >
                            {loadingManualCid ? <ArrowPathIcon className="h-4 w-4 animate-spin"/> : "获取CID"}
                        </button>
                    </div>
                </div>
                <div className="text-xs text-[var(--color-secondary-text)] flex gap-2">
                    <span>海报: <StatusBadge status={pageData.pictures.poster_stats[3]}/></span>
                    <span>壁纸: <StatusBadge status={pageData.pictures.fanart_stats[3]}/></span>
                    <span>缩略图: <StatusBadge status={pageData.pictures.thumb_stats[3]}/></span>
                </div>
            </div>

            <NfoEditor nfoData={pageData.nfo_data} onSave={handleSaveNfo} />

            {isModalOpen && <ImageProcessorModal data={modalData} onClose={(processed) => { setIsModalOpen(false); if (processed) fetchData(); }} />}
        </div>
    );
}

export default HandmadeCorrectionPage;
