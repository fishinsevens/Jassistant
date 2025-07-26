# backend/http_client.py
"""
统一HTTP客户端管理
提供统一的HTTP请求配置和会话管理
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
import time
from typing import Dict, Any, Optional
import threading

logger = logging.getLogger(__name__)

# 统一的HTTP请求头配置
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Keep-Alive': 'timeout=30, max=100'
}

# DMM专用请求头
DMM_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0',
    'Accept': 'image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://www.dmm.co.jp/',
    'Connection': 'keep-alive'
}

# 图片下载专用请求头
IMAGE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Connection': 'keep-alive'
}

class HTTPClientManager:
    """HTTP客户端管理器"""
    
    def __init__(self):
        self._sessions = {}
        self._session_lock = threading.Lock()
        self._stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_response_time': 0.0
        }
        self._stats_lock = threading.Lock()
    
    def create_session(self, 
                      session_name: str = 'default',
                      pool_connections: int = 10,
                      pool_maxsize: int = 20,
                      max_retries: int = 2,
                      backoff_factor: float = 0.5,
                      timeout: int = 30,
                      headers: Optional[Dict[str, str]] = None) -> requests.Session:
        """
        创建优化的HTTP会话
        
        Args:
            session_name: 会话名称
            pool_connections: 连接池大小
            pool_maxsize: 每个连接池的最大连接数
            max_retries: 最大重试次数
            backoff_factor: 重试间隔因子
            timeout: 默认超时时间
            headers: 自定义请求头
            
        Returns:
            配置好的requests.Session对象
        """
        session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"]
        )
        
        # 配置HTTP适配器
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=retry_strategy,
            pool_block=False
        )
        
        # 为HTTP和HTTPS配置适配器
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # 设置默认请求头
        session_headers = headers or DEFAULT_HEADERS.copy()
        session.headers.update(session_headers)
        
        # 设置默认超时
        session.timeout = timeout
        
        logger.info(f"创建HTTP会话: {session_name}")
        return session
    
    def get_session(self, session_name: str = 'default') -> requests.Session:
        """
        获取或创建HTTP会话
        
        Args:
            session_name: 会话名称
            
        Returns:
            HTTP会话对象
        """
        with self._session_lock:
            if session_name not in self._sessions:
                if session_name == 'dmm':
                    self._sessions[session_name] = self.create_session(
                        session_name=session_name,
                        headers=DMM_HEADERS,
                        timeout=4,
                        max_retries=1
                    )
                elif session_name == 'image':
                    self._sessions[session_name] = self.create_session(
                        session_name=session_name,
                        headers=IMAGE_HEADERS,
                        timeout=30,
                        max_retries=3
                    )
                else:
                    self._sessions[session_name] = self.create_session(session_name)
            
            return self._sessions[session_name]
    
    def request(self, method: str, url: str, 
               session_name: str = 'default',
               timeout: Optional[int] = None,
               headers: Optional[Dict[str, str]] = None,
               **kwargs) -> requests.Response:
        """
        发送HTTP请求
        
        Args:
            method: HTTP方法
            url: 请求URL
            session_name: 使用的会话名称
            timeout: 超时时间
            headers: 额外的请求头
            **kwargs: 其他requests参数
            
        Returns:
            HTTP响应对象
        """
        session = self.get_session(session_name)
        
        # 合并请求头
        if headers:
            request_headers = session.headers.copy()
            request_headers.update(headers)
            kwargs['headers'] = request_headers
        
        # 设置超时
        if timeout:
            kwargs['timeout'] = timeout
        elif not kwargs.get('timeout'):
            kwargs['timeout'] = session.timeout
        
        # 记录请求统计
        start_time = time.time()
        try:
            response = session.request(method, url, **kwargs)
            
            # 更新成功统计
            response_time = time.time() - start_time
            with self._stats_lock:
                self._stats['total_requests'] += 1
                self._stats['successful_requests'] += 1
                self._stats['total_response_time'] += response_time
            
            logger.debug(f"HTTP请求成功: {method} {url} - {response.status_code} ({response_time:.2f}s)")
            return response
            
        except Exception as e:
            # 更新失败统计
            response_time = time.time() - start_time
            with self._stats_lock:
                self._stats['total_requests'] += 1
                self._stats['failed_requests'] += 1
                self._stats['total_response_time'] += response_time
            
            logger.error(f"HTTP请求失败: {method} {url} - {e} ({response_time:.2f}s)")
            raise
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """GET请求的便捷方法"""
        return self.request('GET', url, **kwargs)
    
    def post(self, url: str, **kwargs) -> requests.Response:
        """POST请求的便捷方法"""
        return self.request('POST', url, **kwargs)
    
    def put(self, url: str, **kwargs) -> requests.Response:
        """PUT请求的便捷方法"""
        return self.request('PUT', url, **kwargs)
    
    def delete(self, url: str, **kwargs) -> requests.Response:
        """DELETE请求的便捷方法"""
        return self.request('DELETE', url, **kwargs)
    
    def head(self, url: str, **kwargs) -> requests.Response:
        """HEAD请求的便捷方法"""
        return self.request('HEAD', url, **kwargs)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取HTTP客户端统计信息
        
        Returns:
            统计信息字典
        """
        with self._stats_lock:
            stats = self._stats.copy()
        
        # 计算平均响应时间
        if stats['total_requests'] > 0:
            stats['average_response_time'] = stats['total_response_time'] / stats['total_requests']
            stats['success_rate'] = stats['successful_requests'] / stats['total_requests']
        else:
            stats['average_response_time'] = 0.0
            stats['success_rate'] = 0.0
        
        # 添加会话信息
        with self._session_lock:
            stats['active_sessions'] = list(self._sessions.keys())
            stats['session_count'] = len(self._sessions)
        
        return stats
    
    def reset_stats(self):
        """重置统计信息"""
        with self._stats_lock:
            self._stats = {
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'total_response_time': 0.0
            }
    
    def close_session(self, session_name: str):
        """关闭指定会话"""
        with self._session_lock:
            if session_name in self._sessions:
                self._sessions[session_name].close()
                del self._sessions[session_name]
                logger.info(f"关闭HTTP会话: {session_name}")
    
    def close_all_sessions(self):
        """关闭所有会话"""
        with self._session_lock:
            for session_name, session in self._sessions.items():
                session.close()
                logger.info(f"关闭HTTP会话: {session_name}")
            self._sessions.clear()

# 创建全局HTTP客户端管理器实例
http_client = HTTPClientManager()

# 向后兼容的函数和变量
def create_optimized_session(**kwargs):
    """向后兼容：创建优化的会话"""
    return http_client.create_session(**kwargs)

# 导出常用的请求头配置
HTTP_HEADERS = DEFAULT_HEADERS
