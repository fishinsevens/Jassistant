import { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import {
    MagnifyingGlassIcon,
    ArrowPathIcon,
    LinkIcon,
    PhotoIcon,
    ArchiveBoxXMarkIcon,
    ArrowUpTrayIcon,
    CheckCircleIcon,
    XCircleIcon
} from '@heroicons/react/24/outline';
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

const ActionPanel = ({ movie, pictures, onRefresh, onSkip, onOpenModal, onUploadLocal }) => {
    const [dmmInfo, setDmmInfo] = useState(null);
    const [loading, setLoading] = useState(false);
    // 添加手动输入番号的状态
    const [manualBangou, setManualBangou] = useState('');
    const [loadingManualCid, setLoadingManualCid] = useState(false);
    // 使用链接验证Hook
    const {
        linkVerificationStatus,
        verifyLinks,
        refreshLinkVerification
    } = useLinkVerification();



    const handleSearch = useCallback(() => {
        if (!movie) return;
        setLoading(true);
        axios.get(`/api/get-dmm-info?bangou=${movie.bangou}`)
            .then(res => {
                setDmmInfo(res.data);
                // 自动触发链接验证
                if (res.data.success && res.data.results) {
                    verifyLinks(res.data.results);
                }
            })
            .catch(err => setDmmInfo({ error: err.response?.data?.message || "查询失败" }))
            .finally(() => setLoading(false));
    }, [movie]);

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

    // 移除自动获取DMM信息
    useEffect(() => {
        setDmmInfo(null);
    }, [movie]);

    const dmmResult = dmmInfo?.results?.[0];

    return (
        <div className="bg-[var(--color-sidebar-bg)] p-3 rounded-lg flex items-center justify-between gap-4 mb-4">
            <div className="flex items-center gap-4">
                {/* 添加本地上传按钮 */}
                <button 
                    onClick={onUploadLocal}
                    className="flex items-center gap-1 bg-[var(--color-secondary-accent)] text-white px-3 py-1 rounded-md text-sm hover:opacity-80"
                >
                    <ArrowUpTrayIcon className="h-4 w-4" /> 上传本地图片
                </button>

                {loading ? <ArrowPathIcon className="h-6 w-6 animate-spin text-[var(--color-primary-text)]"/> : (
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
                                onClick={() => onOpenModal(dmmResult.wallpaper_url.url, 'fanart')}
                                title="处理壁纸"
                                className="text-[var(--color-primary-text)] hover:text-[var(--color-primary-accent)]"
                            >
                                <PhotoIcon className="h-6 w-6"/>
                            </button>
                            <button
                                onClick={() => onOpenModal(dmmResult.cover_url.url, 'poster')}
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
                                onClick={handleSearch}
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
            <div className="flex items-center gap-2">
                <div className="text-xs text-[var(--color-secondary-text)] flex gap-2 border-r border-[var(--color-border)] pr-2 mr-2">
                    <span>海报: <StatusBadge status={pictures?.poster_status}/></span>
                    <span>壁纸: <StatusBadge status={pictures?.fanart_status}/></span>
                </div>
                <button onClick={onRefresh} className="p-2 rounded-md hover:bg-[var(--color-secondary-bg)]" title="刷新图片状态"><ArrowPathIcon className="h-5 w-5"/></button>
                <button onClick={onSkip} className="p-2 rounded-md hover:bg-[var(--color-secondary-bg)]" title="跳过低画质处理"><ArchiveBoxXMarkIcon className="h-5 w-5"/></button>
            </div>
        </div>
    );
};

const NfoEditor = ({ nfoData, onSave }) => {
    const [editorData, setEditorData] = useState({});
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
    const handleSave = () => {
        const dataToSave = { ...editorData };
        for (const key of ['actors', 'genres', 'tags', 'sets']) {
            if (typeof dataToSave[key] === 'string') {
                dataToSave[key] = dataToSave[key].split(',').map(s => s.trim()).filter(Boolean);
            }
        }
        onSave(dataToSave);
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
                        placeholder="发行日期" 
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
                <div className="flex flex-col">
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
            <button onClick={handleSave} className="bg-[var(--color-primary-accent)] text-white px-4 py-2 rounded-md text-sm font-semibold hover:bg-opacity-80 mt-4">保存NFO</button>
        </div>
    );
};

function ManualProcessPage() {
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState([]);
    const [selectedMovie, setSelectedMovie] = useState(null);
    const [movieDetails, setMovieDetails] = useState(null);
    const [selectedNfoId, setSelectedNfoId] = useState('');
    const [nfoData, setNfoData] = useState(null);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [modalData, setModalData] = useState(null);
    const fileInputRef = useRef(null);
    
    const fetchMovieDetails = useCallback((movieId) => {
        axios.get(`/api/manual/movie-details/${movieId}`)
            .then(res => {
                setMovieDetails(res.data);
                if (res.data.nfo_files && res.data.nfo_files.length > 0) {
                    handleNfoSelect(res.data.nfo_files[0].id);
                } else {
                    setSelectedNfoId('');
                    setNfoData(null);
                }
            });
    }, []);

    const handleSelectMovie = useCallback((movie) => {
        setSelectedMovie(movie);
        setSearchResults([]);
    }, []);

    useEffect(() => {
        if (selectedMovie) {
            fetchMovieDetails(selectedMovie.id);
        }
    }, [selectedMovie, fetchMovieDetails]);
    
    const handleNfoSelect = (nfoId) => {
        setSelectedNfoId(nfoId);
        axios.get(`/api/manual/nfo-content/${nfoId}`)
            .then(res => setNfoData(res.data));
    };

    const handleSearch = (e) => {
        e.preventDefault();
        if (searchQuery.length < 2) return;
        axios.get(`/api/manual/find-movie?q=${searchQuery}`)
            .then(res => setSearchResults(res.data));
    };

    const [saveResult, setSaveResult] = useState({ show: false, success: false, message: "" });

    const handleSaveNfo = (newData) => {
        setSaveResult({ show: true, success: false, message: "正在保存..." });
        axios.post(`/api/manual/save-nfo/${selectedNfoId}`, newData)
            .then(res => {
                setSaveResult({ show: true, success: true, message: res.data.message || "保存成功" });
                setTimeout(() => setSaveResult({ show: false, success: false, message: "" }), 3000);
            })
            .catch(err => {
                const errorMsg = err.response?.data?.message || err.message || "保存失败";
                setSaveResult({ show: true, success: false, message: `错误: ${errorMsg}` });
                setTimeout(() => setSaveResult({ show: false, success: false, message: "" }), 5000);
            });
    };
    
    const handleRefresh = useCallback(() => {
        if (selectedMovie) fetchMovieDetails(selectedMovie.id);
    }, [selectedMovie, fetchMovieDetails]);

    const handleSkip = () => {
        if (selectedMovie) {
            axios.post(`/api/skip-item/${selectedMovie.id}`).then(() => {
                alert("已标记为跳过");
                handleRefresh();
            });
        }
    };

    const openImageProcessor = (imageUrl, imageType) => {
        setModalData({ item_id: selectedMovie.id, image_url: imageUrl, image_type: imageType, bangou: selectedMovie.bangou });
        setIsModalOpen(true);
    };
    
    // 处理本地图片上传
    const handleFileChange = (e) => {
        const file = e.target.files[0];
        if (!file || !selectedMovie) return;
        
        // 创建临时URL
        const tempUrl = URL.createObjectURL(file);
        setModalData({ 
            item_id: selectedMovie.id, 
            image_url: tempUrl, 
            image_type: 'fanart',  // 默认作为fanart处理
            bangou: selectedMovie.bangou,
            localFile: file  // 传递本地文件对象
        });
        setIsModalOpen(true);
    };
    
    const handleUploadClick = () => {
        if (!selectedMovie) {
            alert("请先选择一个电影项目");
            return;
        }
        fileInputRef.current?.click();
    };

    const posterUrl = getImageUrl(movieDetails?.pictures?.poster_path);
    const thumbUrl = getImageUrl(movieDetails?.pictures?.thumb_path);

    return (
        <div className="h-full">
            <h1 className="text-4xl font-bold text-[var(--color-primary-text)] mb-6">数据清洗</h1>
            <form onSubmit={handleSearch} className="flex gap-2 mb-4 relative">
                <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="输入番号或路径..." className="input-field flex-grow"/>
                <button type="submit" className="bg-[var(--color-primary-accent)] text-white px-4 py-2 rounded-md text-sm font-semibold hover:bg-opacity-80"><MagnifyingGlassIcon className="h-5 w-5"/></button>
                {searchResults.length > 0 && (
                    <div className="absolute top-full left-0 right-0 bg-[var(--color-sidebar-bg)] border border-[var(--color-border)] rounded-b-lg z-10 max-h-60 overflow-y-auto">
                        {searchResults.map(movie => (
                            <div key={movie.id} onClick={() => handleSelectMovie(movie)} className="p-2 hover:bg-[var(--color-primary-accent)] cursor-pointer">
                                <p className="font-bold">{movie.bangou}</p>
                                <p className="text-xs text-[var(--color-secondary-text)]">{movie.item_path}</p>
                            </div>
                        ))}
                    </div>
                )}
            </form>

            {selectedMovie && (
                <div className="mt-6 max-w-7xl mx-auto">
                    <div className="flex items-center gap-4 mb-4">
                        <span className="font-bold text-lg text-[var(--color-primary-text)]">NFO 文件:</span>
                        <select value={selectedNfoId} onChange={(e) => handleNfoSelect(e.target.value)} className="input-field">
                            {movieDetails?.nfo_files.length > 0 ? 
                                movieDetails.nfo_files.map(nfo => <option key={nfo.id} value={nfo.id}>{nfo.nfo_path.split('/').pop()}</option>) :
                                <option disabled>未找到NFO文件</option>
                            }
                        </select>
                    </div>

                    <ActionPanel 
                        movie={selectedMovie} 
                        pictures={movieDetails?.pictures} 
                        onRefresh={handleRefresh} 
                        onSkip={handleSkip} 
                        onOpenModal={openImageProcessor}
                        onUploadLocal={handleUploadClick}
                    />
                    
                    <input 
                        type="file" 
                        ref={fileInputRef}
                        className="hidden" 
                        accept="image/*"
                        onChange={handleFileChange}
                    />
                    
                    <NfoEditor nfoData={nfoData} onSave={handleSaveNfo} />
                    {saveResult.show && (
                        <div className={`mt-4 p-2 rounded-md text-sm ${saveResult.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                            {saveResult.message}
                        </div>
                    )}
                </div>
            )}
            {isModalOpen && <ImageProcessorModal data={modalData} onClose={(processed) => { setIsModalOpen(false); if (processed) handleRefresh(); }} />}
        </div>
    );
}

export default ManualProcessPage;
