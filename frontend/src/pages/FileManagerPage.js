import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import {
    FolderIcon,
    DocumentIcon,
    ArrowUturnLeftIcon,
    ArrowPathIcon,
    HomeIcon,
    MagnifyingGlassIcon,
    PlusIcon,
    TrashIcon,
    PencilIcon,
    ClipboardDocumentIcon,
    CheckCircleIcon
} from '@heroicons/react/24/outline';

const formatBytes = (bytes, decimals = 2) => {
    if (!bytes || bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

const formatDate = (timestamp) => {
    return new Date(timestamp * 1000).toLocaleString();
};

const FileListItem = ({ item, onNavigate, onSelect, isSelected }) => {
    const navigate = useNavigate();

    const handleDoubleClick = () => {
        if (item.is_directory) {
            onNavigate(item.path);
        } else if (item.name.toLowerCase().endsWith('.nfo')) {
            navigate('/handmade-correction', { state: { nfoPath: item.path } });
        }
    };

    return (
        <div
            onDoubleClick={handleDoubleClick}
            onClick={() => onSelect(item.path)}
            className={`flex items-center p-2 rounded-md hover:bg-[var(--color-sidebar-bg)] cursor-pointer transition-colors duration-150 ${isSelected ? 'bg-[var(--color-primary-accent)]' : ''}`}
        >
            <div className="flex items-center gap-3 w-1/2">
                {item.is_directory ?
                    <FolderIcon className="h-6 w-6 text-yellow-400 flex-shrink-0"/> :
                    <DocumentIcon className="h-6 w-6 text-[var(--color-secondary-text)] flex-shrink-0"/>
                }
                <span className="text-sm text-[var(--color-primary-text)] truncate" title={item.name}>{item.name}</span>
            </div>
            <div className="w-1/4 text-right text-sm text-[var(--color-secondary-text)]">{formatDate(item.modified_at)}</div>
            <div className="w-1/4 text-right text-sm text-[var(--color-secondary-text)]">{!item.is_directory ? formatBytes(item.size) : '--'}</div>
        </div>
    );
};

// 修改fetchFiles函数以支持简单模式选项
const fetchFiles = async (path, page = 1, page_size = 200, simple = false, retries = 2) => {
  try {
    const response = await axios.get(`/api/files/list`, {
      params: {
        path,
        page,
        page_size,
        simple
      },
      // 增加超时时间
      timeout: 30000 // 30秒
    });
    return response.data;
  } catch (error) {
    // 实现自动重试
    if (retries > 0) {
      console.warn(`获取文件列表失败，尝试重试 (${retries})...`);
      // 如果常规模式失败，尝试使用简单模式重试
      return fetchFiles(path, page, page_size, true, retries - 1);
    }
    console.error("获取文件列表失败", error);
    throw error;
  }
};

function FileManagerPage() {
    const [mediaRoot, setMediaRoot] = useState('');
    const [currentPath, setCurrentPath] = useState('');
    const [pathInput, setPathInput] = useState('');
    const [multiSelectEnabled, setMultiSelectEnabled] = useState(false);
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedItems, setSelectedItems] = useState([]);
    const [searchTerm, setSearchTerm] = useState('');
    const [copiedPath, setCopiedPath] = useState(null);
    const [error, setError] = useState(null); // 添加错误状态
    const [retrying, setRetrying] = useState(false); // 添加重试状态
    const [settingsLoaded, setSettingsLoaded] = useState(false);

    // 分页相关状态
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalItems, setTotalItems] = useState(0);
    const [pageSize, setPageSize] = useState(200);
    const [loadingMore, setLoadingMore] = useState(false);
    
    // 在组件挂载时获取媒体根路径设置
    useEffect(() => {
        setLoading(true); // 显示加载状态，避免空白界面
        axios.get('/api/settings')
            .then(res => {
                const root = res.data.media_root || '/weiam';
                setMediaRoot(root);
                setCurrentPath(root);
                setPathInput(root);
                setSettingsLoaded(true); // 标记设置已加载
            })
            .catch(err => {
                console.error("获取设置失败:", err);
                // 默认使用/weiam作为备选
                setMediaRoot('/weiam');
                setCurrentPath('/weiam');
                setPathInput('/weiam');
                setSettingsLoaded(true); // 即使出错也标记为已加载
            });
    }, []);

    const loadFiles = useCallback((path, newPage = 1, append = false) => {
        // 确保路径非空
        if (!path) {
            console.warn("尝试加载空路径");
            return;
        }

        setError(null); // 重置错误
        
        if (newPage === 1) {
            setLoading(true);
            setSelectedItems([]);
        } else {
            setLoadingMore(true);
        }

        // 首次尝试使用标准模式
        const useSimpleMode = false;

        fetchFiles(path, newPage, pageSize, useSimpleMode)
            .then(data => {
                // 处理成功响应
                // 添加排序逻辑 - 目录优先，然后按名称排序
                const sortedItems = [...(data.items || [])].sort((a, b) => {
                    // 首先按目录/文件类型排序
                    if (a.is_directory !== b.is_directory) {
                        return a.is_directory ? -1 : 1;
                    }
                    // 然后按名称排序
                    return a.name.localeCompare(b.name);
                });

                if (append) {
                    setItems(prev => [...prev, ...sortedItems]);
                } else {
                    setItems(sortedItems);
                }

                // 更新分页信息
                setCurrentPage(data.pagination?.page || 1);
                setTotalPages(data.pagination?.total_pages || 1);
                setTotalItems(data.pagination?.total_items || data.items.length);
                setCurrentPath(path);
                setRetrying(false); // 重置重试状态
            })
            .catch(err => {
                console.error("加载文件失败", err);
                // 显示更友好的错误消息
                const errorMsg = err.response?.data?.error || err.message || "加载文件失败";
                setError(`加载失败: ${errorMsg}`);

                // 如果是超时错误，提示用户
                if (err.code === 'ECONNABORTED' || err.message.includes('timeout')) {
                    setError("请求超时，目录可能包含太多文件。请尝试使用简单模式。");
                }
            })
            .finally(() => {
                setLoading(false);
                setLoadingMore(false);
            });
    }, [pageSize]);

    // 添加简单模式加载功能
    const handleSimpleModeLoad = () => {
        setRetrying(true);
        setError(null);
        setLoading(true);

        // 使用简单模式重新加载
        fetchFiles(currentPath, 1, pageSize, true)
            .then(data => {
                // 简单模式下的数据处理
                const sortedItems = [...(data.items || [])].sort((a, b) => {
                    if (a.is_directory !== b.is_directory) {
                        return a.is_directory ? -1 : 1;
                    }
                    return a.name.localeCompare(b.name);
                });

                setItems(sortedItems);
                setCurrentPage(data.pagination?.page || 1);
                setTotalPages(data.pagination?.total_pages || 1);
                setTotalItems(data.pagination?.total_items || data.items.length);
            })
            .catch(err => {
                console.error("简单模式加载失败", err);
                setError(`简单模式加载失败: ${err.response?.data?.error || err.message}`);
            })
            .finally(() => {
                setLoading(false);
                setRetrying(false);
            });
    };

    // 加载更多文件
    const handleLoadMore = () => {
        if (currentPage < totalPages && !loadingMore) {
            const nextPage = currentPage + 1;
            loadFiles(currentPath, nextPage, true);
            setCurrentPage(nextPage);
        }
    };

    // 仅在设置加载完成后加载文件
    useEffect(() => {
        if (settingsLoaded && currentPath) {
            loadFiles(currentPath);
        }
    }, [currentPath, loadFiles, settingsLoaded]);

    useEffect(() => {
        setPathInput(currentPath);
    }, [currentPath]);

    const filteredItems = useMemo(() => {
        if (!searchTerm) return items;
        return items.filter(item => item.name.toLowerCase().includes(searchTerm.toLowerCase()));
    }, [items, searchTerm]);

    const handleNavigate = (path) => {
        if (!path.startsWith(mediaRoot)) {
            alert(`路径必须在 ${mediaRoot} 目录下。`);
            setPathInput(currentPath);
            return;
        }
        setCurrentPath(path);
    };

    const handleGoUp = () => {
        if (currentPath === mediaRoot) return;
        const parentPath = currentPath.substring(0, currentPath.lastIndexOf('/')) || mediaRoot;
        handleNavigate(parentPath);
    };

    const handleSelect = (path) => {
        if (multiSelectEnabled) {
            setSelectedItems(prev => prev.includes(path) ? prev.filter(p => p !== path) : [...prev, path]);
        } else {
            setSelectedItems(prev => (prev.includes(path) ? [] : [path]));
        }
    };

    const handleDelete = () => {
        if (selectedItems.length === 0) return;
        if (window.confirm(`确定要删除选中的 ${selectedItems.length} 个项目吗？`)) {
            axios.post('/api/files/delete', { paths: selectedItems })
                .then(() => loadFiles(currentPath))
                .catch(err => alert(`删除失败: ${err.response?.data?.error || err.message}`));
        }
    };

    const handleCreateDir = () => {
        const dirName = prompt("请输入新目录的名称:");
        if (dirName) {
            axios.post('/api/files/create-dir', { path: currentPath, name: dirName })
                .then(() => loadFiles(currentPath))
                .catch(err => alert(`创建目录失败: ${err.response?.data?.error || err.message}`));
        }
    };

    const handleRename = () => {
        if (selectedItems.length !== 1) return alert("请只选择一个项目进行重命名。");
        const oldPath = selectedItems[0];
        const oldName = oldPath.split('/').pop();
        const newName = prompt("请输入新的名称:", oldName);
        if (newName && newName !== oldName) {
            axios.post('/api/files/rename', { path: oldPath, new_name: newName })
                .then(() => loadFiles(currentPath))
                .catch(err => alert(`重命名失败: ${err.response?.data?.error || err.message}`));
        }
    };

    const handleCopyPath = () => {
        if (selectedItems.length !== 1) return alert("请只选择一个项目来复制路径。");
        const path = selectedItems[0];
        const textArea = document.createElement("textarea");
        textArea.value = path;
        textArea.style.position = "fixed";
        textArea.style.left = "-9999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        try {
            document.execCommand('copy');
            setCopiedPath(path);
            setTimeout(() => setCopiedPath(null), 2000);
        } catch (err) {
            alert('复制路径失败!');
        }
        document.body.removeChild(textArea);
    };

    // 渲染分页控件
    const renderPagination = () => {
        if (totalPages <= 1) return null;

        return (
            <div className="flex justify-center items-center my-4">
                {currentPage < totalPages && (
                    <button
                        onClick={handleLoadMore}
                        disabled={loadingMore}
                        className="flex items-center gap-2 bg-[var(--color-primary-accent)] text-white px-4 py-2 rounded-md disabled:opacity-50"
                    >
                        {loadingMore && <ArrowPathIcon className="h-4 w-4 animate-spin" />}
                        加载更多 ({currentPage}/{totalPages} 页, 共{totalItems}项)
                    </button>
                )}
                {currentPage === totalPages && (
                    <div className="text-[var(--color-secondary-text)] text-sm">
                        已显示全部 {totalItems} 项
                    </div>
                )}
            </div>
        );
    };

    // 修改错误显示
    const renderError = () => {
        if (!error) return null;

        return (
            <div className="p-4 bg-red-100 border border-red-400 text-red-700 rounded-md mb-4">
                <div className="font-bold mb-1">错误</div>
                <div>{error}</div>
                {error.includes('超时') && (
                    <button
                        onClick={handleSimpleModeLoad}
                        disabled={retrying}
                        className="mt-2 bg-red-600 text-white px-3 py-1 rounded-md text-sm hover:bg-red-700 disabled:opacity-50"
                    >
                        {retrying ? "加载中..." : "使用简单模式重新加载"}
                    </button>
                )}
            </div>
        );
    };

    return (
        <div className="flex flex-col h-full bg-[var(--color-secondary-bg)] rounded-lg p-4">
            <h1 className="text-2xl font-bold text-[var(--color-primary-text)] mb-4">文件管理</h1>
            {/* --- 关键修正：响应式工具栏 --- */}
            <div className="flex flex-col md:flex-row md:items-center gap-2 mb-4 p-2 bg-[var(--color-sidebar-bg)] rounded-md">
                <div className="flex items-center gap-2 flex-shrink-0">
                    <button onClick={() => handleNavigate(mediaRoot)} className="p-2 rounded-md hover:bg-[var(--color-primary-accent)]" title="主目录"><HomeIcon className="h-5 w-5"/></button>
                    <button onClick={handleGoUp} disabled={currentPath === mediaRoot} className="p-2 rounded-md hover:bg-[var(--color-primary-accent)] disabled:opacity-50" title="返回上级"><ArrowUturnLeftIcon className="h-5 w-5"/></button>
                    <button onClick={() => loadFiles(currentPath)} className="p-2 rounded-md hover:bg-[var(--color-primary-accent)]" title="刷新"><ArrowPathIcon className="h-5 w-5"/></button>
                </div>
                <div className="flex items-center gap-2 w-full md:flex-grow">
                    <input type="text" value={pathInput} onChange={(e) => setPathInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') handleNavigate(pathInput); }} className="input-field flex-grow h-10 min-w-0"/>
                    <button onClick={() => handleNavigate(pathInput)} className="bg-[var(--color-primary-accent)] text-white p-2 rounded-md h-10 flex-shrink-0">前往</button>
                </div>
                <div className="relative flex-shrink-0">
                    <MagnifyingGlassIcon className="h-5 w-5 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-secondary-text)]"/>
                    <input type="text" placeholder="搜索..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="input-field p-2 pl-10 h-10"/>
                </div>
            </div>
            <div className="flex flex-wrap items-center gap-2 mb-4">
                <button onClick={() => setMultiSelectEnabled(!multiSelectEnabled)} className={`flex items-center px-3 py-1 rounded-md text-sm ${multiSelectEnabled ? 'bg-[var(--color-primary-accent)] text-white' : 'bg-[var(--color-sidebar-bg)] text-[var(--color-primary-text)] hover:bg-opacity-80'}`}>
                    {multiSelectEnabled ? '多选已激活' : '激活多选'}
                </button>
                <button onClick={handleCreateDir} className="flex items-center bg-[var(--color-sidebar-bg)] text-[var(--color-primary-text)] px-3 py-1 rounded-md text-sm hover:bg-opacity-80"><PlusIcon className="h-5 w-5 mr-1"/>创建目录</button>
                <button onClick={handleRename} disabled={selectedItems.length !== 1} className="flex items-center bg-[var(--color-sidebar-bg)] text-[var(--color-primary-text)] px-3 py-1 rounded-md text-sm hover:bg-opacity-80 disabled:opacity-50"><PencilIcon className="h-5 w-5 mr-1"/>重命名</button>
                <button onClick={handleCopyPath} disabled={selectedItems.length !== 1} className="flex items-center bg-[var(--color-sidebar-bg)] text-[var(--color-primary-text)] px-3 py-1 rounded-md text-sm hover:bg-opacity-80 disabled:opacity-50">
                    {copiedPath === selectedItems[0] ? <CheckCircleIcon className="h-5 w-5 mr-1 text-[var(--color-secondary-accent)]"/> : <ClipboardDocumentIcon className="h-5 w-5 mr-1"/>}
                    复制路径
                </button>
                <button onClick={handleDelete} disabled={selectedItems.length === 0} className="flex items-center bg-[var(--color-danger)] text-white px-3 py-1 rounded-md text-sm hover:bg-opacity-80 disabled:opacity-50"><TrashIcon className="h-5 w-5 mr-1"/>删除</button>
                <span className="ml-auto text-[var(--color-secondary-text)] text-sm">{selectedItems.length} / {items.length} 已选择</span>
            </div>
            <div className="flex-grow overflow-y-auto" style={{ minHeight: '400px' }}>
                {renderError()}
                {loading ? (
                    <div className="flex justify-center items-center h-full"><ArrowPathIcon className="h-8 w-8 animate-spin text-[var(--color-primary-accent)]"/></div>
                ) : (
                    <div className="flex flex-col">
                        <div className="flex items-center border-b border-[var(--color-border)] p-2 text-sm font-bold text-[var(--color-secondary-text)] sticky top-0 bg-[var(--color-secondary-bg)]">
                            <div className="w-1/2">名称</div>
                            <div className="w-1/4 text-right">修改日期</div>
                            <div className="w-1/4 text-right">大小</div>
                        </div>
                        {filteredItems.map(item => (
                            <FileListItem
                                key={item.path}
                                item={item}
                                onNavigate={handleNavigate}
                                onSelect={handleSelect}
                                isSelected={selectedItems.includes(item.path)}
                            />
                        ))}
                        {/* 添加分页控件 */}
                        {renderPagination()}
                    </div>
                )}
            </div>
        </div>
    );
}

export default FileManagerPage;
