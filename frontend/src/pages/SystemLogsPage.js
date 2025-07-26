import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import {
    ArrowPathIcon,
    TrashIcon,
    FunnelIcon,
    XMarkIcon
} from '@heroicons/react/24/outline';

// 日志等级对应的颜色
const LOG_LEVEL_COLORS = {
    'DEBUG': 'text-blue-500',
    'INFO': 'text-green-500',
    'WARNING': 'text-yellow-500',
    'ERROR': 'text-red-500',
    'CRITICAL': 'text-purple-500'
};

function SystemLogsPage() {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [totalLines, setTotalLines] = useState(0);
    const [maxLines, setMaxLines] = useState(500);
    const [filterLevel, setFilterLevel] = useState('');
    const logTableRef = useRef(null);
    
    // 获取系统日志
    const fetchLogs = async () => {
        setLoading(true);
        try {
            const response = await axios.get(`/api/system-logs?max_lines=${maxLines}${filterLevel ? `&level=${filterLevel}` : ''}`);
            if (response.data.success) {
                setLogs(response.data.logs);
                setTotalLines(response.data.total_lines);
            } else {
                console.error("获取日志失败:", response.data.message);
            }
        } catch (error) {
            console.error("获取日志出错:", error);
        } finally {
            setLoading(false);
        }
    };

    // 清除系统日志
    const clearLogs = async () => {
        if (!window.confirm('确定要清除所有系统日志吗？此操作不可撤销。')) return;
        
        try {
            const response = await axios.post('/api/system-logs/clear');
            if (response.data.success) {
                alert('日志已成功清除');
                fetchLogs();
            } else {
                alert(`清除失败: ${response.data.message}`);
            }
        } catch (error) {
            alert(`清除失败: ${error.response?.data?.message || error.message}`);
        }
    };
    
    // 更改过滤日志等级
    const handleFilterChange = (level) => {
        if (filterLevel === level) {
            setFilterLevel(''); // 再次点击相同级别则取消过滤
        } else {
            setFilterLevel(level);
        }
    };
    
    // 清除过滤
    const clearFilter = () => {
        setFilterLevel('');
    };
    
    // 首次加载获取日志
    useEffect(() => {
        fetchLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);
    
    // 当过滤条件或最大行数改变时重新获取日志
    useEffect(() => {
        fetchLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [filterLevel, maxLines]);
    
    // 当日志更新时滚动到底部
    useEffect(() => {
        if (logTableRef.current && !loading) {
            logTableRef.current.scrollTop = logTableRef.current.scrollHeight;
        }
    }, [logs, loading]);

    return (
        <div className="h-full flex flex-col">
            <div className="flex justify-between items-center mb-4">
                <h1 className="text-4xl font-bold text-[var(--color-primary-text)] mb-2">系统日志</h1>
                
                <div className="flex items-center gap-3">
                    <div className="flex items-center">
                        <label className="mr-2 text-sm text-[var(--color-secondary-text)]">最大行数:</label>
                        <select 
                            value={maxLines} 
                            onChange={(e) => setMaxLines(Number(e.target.value))}
                            className="input-field text-sm py-1 w-24"
                        >
                            <option value="100">100行</option>
                            <option value="500">500行</option>
                            <option value="1000">1000行</option>
                            <option value="5000">5000行</option>
                            <option value="10000">10000行</option>
                        </select>
                    </div>
                    
                    <div className="flex items-center gap-2">
                        <span className="text-[var(--color-secondary-text)] text-sm">过滤级别:</span>
                        <div className="flex gap-1">
                            {['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'].map(level => (
                                <button
                                    key={level}
                                    onClick={() => handleFilterChange(level)}
                                    className={`px-2 py-0.5 text-xs rounded ${filterLevel === level 
                                        ? 'bg-[var(--color-primary-accent)] text-white' 
                                        : `bg-[var(--color-sidebar-bg)] ${LOG_LEVEL_COLORS[level]}`}`}
                                >
                                    {level}
                                </button>
                            ))}
                            {filterLevel && (
                                <button 
                                    onClick={clearFilter}
                                    className="text-[var(--color-secondary-text)] hover:text-[var(--color-primary-accent)]"
                                    title="清除过滤"
                                >
                                    <XMarkIcon className="h-4 w-4" />
                                </button>
                            )}
                        </div>
                    </div>
                    
                    <button 
                        onClick={fetchLogs} 
                        className="p-2 rounded-md bg-[var(--color-primary-accent)] text-white"
                        title="刷新日志"
                    >
                        <ArrowPathIcon className={`h-5 w-5 ${loading ? 'animate-spin' : ''}`} />
                    </button>
                    
                    <button 
                        onClick={clearLogs} 
                        className="p-2 rounded-md bg-[var(--color-danger)] text-white"
                        title="清除所有日志"
                    >
                        <TrashIcon className="h-5 w-5" />
                    </button>
                </div>
            </div>
            
            <div className="text-[var(--color-secondary-text)] mb-2 text-sm flex justify-between">
                <div>
                    总行数: <span className="font-bold">{totalLines}</span> 
                    {filterLevel && <span className="ml-2">过滤为: <span className="font-bold">{filterLevel}</span></span>}
                </div>
            </div>
            
            <div 
                ref={logTableRef}
                className="flex-grow overflow-auto bg-[var(--color-sidebar-bg)] rounded-lg border border-[var(--color-border)]"
            >
                <table className="min-w-full divide-y divide-[var(--color-border)]">
                    <thead className="bg-[var(--color-secondary-bg)] sticky top-0 z-10">
                        <tr>
                            <th scope="col" className="px-3 py-2 text-left text-xs font-medium text-[var(--color-secondary-text)] w-48">
                                时间
                            </th>
                            <th scope="col" className="px-3 py-2 text-left text-xs font-medium text-[var(--color-secondary-text)] w-24">
                                级别
                            </th>
                            <th scope="col" className="px-3 py-2 text-left text-xs font-medium text-[var(--color-secondary-text)] w-32">
                                线程
                            </th>
                            <th scope="col" className="px-3 py-2 text-left text-xs font-medium text-[var(--color-secondary-text)]">
                                内容
                            </th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--color-border)]">
                        {loading && logs.length === 0 ? (
                            <tr>
                                <td colSpan="4" className="text-center py-4 text-[var(--color-secondary-text)]">
                                    加载中...
                                </td>
                            </tr>
                        ) : logs.length > 0 ? (
                            logs.map((log, index) => (
                                <tr key={index} className={index % 2 === 0 ? 'bg-[var(--color-sidebar-bg)]' : 'bg-[var(--color-secondary-bg)] bg-opacity-30'}>
                                    <td className="px-3 py-1 text-xs text-[var(--color-secondary-text)]">
                                        {log.timestamp}
                                    </td>
                                    <td className={`px-3 py-1 text-xs font-medium ${LOG_LEVEL_COLORS[log.level] || 'text-[var(--color-secondary-text)]'}`}>
                                        {log.level}
                                    </td>
                                    <td className="px-3 py-1 text-xs text-[var(--color-secondary-text)]">
                                        {log.thread}
                                    </td>
                                    <td className="px-3 py-1 text-xs text-[var(--color-primary-text)] whitespace-pre-wrap break-all">
                                        {log.message}
                                    </td>
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td colSpan="4" className="text-center py-4 text-[var(--color-secondary-text)]">
                                    没有找到日志记录
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

export default SystemLogsPage; 