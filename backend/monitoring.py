# backend/monitoring.py
"""
系统监控与告警模块
包括性能监控、业务监控和告警机制
"""
import time
import threading
import psutil
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import deque
import json

logger = logging.getLogger(__name__)

@dataclass
class MetricPoint:
    """监控指标数据点"""
    timestamp: float
    value: float
    tags: Dict[str, str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class Alert:
    """告警信息"""
    id: str
    metric_name: str
    level: str  # 'warning', 'critical'
    message: str
    timestamp: float
    resolved: bool = False
    resolved_at: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class MetricCollector:
    """指标收集器"""
    
    def __init__(self, max_points: int = 1000):
        self.metrics = {}
        self.max_points = max_points
        self.lock = threading.RLock()
    
    def record(self, metric_name: str, value: float, tags: Dict[str, str] = None) -> None:
        """记录指标值"""
        with self.lock:
            if metric_name not in self.metrics:
                self.metrics[metric_name] = deque(maxlen=self.max_points)
            
            point = MetricPoint(
                timestamp=time.time(),
                value=value,
                tags=tags or {}
            )
            
            self.metrics[metric_name].append(point)
    
    def get_metric_history(self, metric_name: str, 
                          duration_seconds: int = 3600) -> List[MetricPoint]:
        """获取指标历史数据"""
        with self.lock:
            if metric_name not in self.metrics:
                return []
            
            cutoff_time = time.time() - duration_seconds
            return [
                point for point in self.metrics[metric_name]
                if point.timestamp >= cutoff_time
            ]
    
    def get_latest_value(self, metric_name: str) -> Optional[float]:
        """获取最新指标值"""
        with self.lock:
            if metric_name not in self.metrics or not self.metrics[metric_name]:
                return None
            return self.metrics[metric_name][-1].value
    
    def get_average(self, metric_name: str, duration_seconds: int = 300) -> Optional[float]:
        """获取指定时间内的平均值"""
        history = self.get_metric_history(metric_name, duration_seconds)
        if not history:
            return None
        
        return sum(point.value for point in history) / len(history)
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有指标的当前状态"""
        with self.lock:
            result = {}
            for metric_name, points in self.metrics.items():
                if points:
                    latest = points[-1]
                    result[metric_name] = {
                        'latest_value': latest.value,
                        'latest_timestamp': latest.timestamp,
                        'point_count': len(points),
                        'avg_5min': self.get_average(metric_name, 300),
                        'avg_1hour': self.get_average(metric_name, 3600)
                    }
            return result

class SystemMonitor:
    """系统性能监控器"""
    
    def __init__(self, collector: MetricCollector):
        self.collector = collector
        self.monitoring = False
        self.monitor_thread = None
        self.interval = 30  # 30秒采集一次
    
    def start_monitoring(self) -> None:
        """开始监控"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("系统监控已启动")
    
    def stop_monitoring(self) -> None:
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("系统监控已停止")
    
    def _monitor_loop(self) -> None:
        """监控循环"""
        while self.monitoring:
            try:
                self._collect_system_metrics()
                time.sleep(self.interval)
            except Exception as e:
                logger.error(f"系统监控采集失败: {e}")
                time.sleep(self.interval)
    
    def _collect_system_metrics(self) -> None:
        """收集系统指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            self.collector.record('system.cpu.usage_percent', cpu_percent)
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            self.collector.record('system.memory.usage_percent', memory.percent)
            self.collector.record('system.memory.available_mb', memory.available / (1024 * 1024))
            self.collector.record('system.memory.used_mb', memory.used / (1024 * 1024))
            
            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            self.collector.record('system.disk.usage_percent', disk_usage_percent)
            self.collector.record('system.disk.free_gb', disk.free / (1024 * 1024 * 1024))
            
            # 网络IO
            net_io = psutil.net_io_counters()
            self.collector.record('system.network.bytes_sent', net_io.bytes_sent)
            self.collector.record('system.network.bytes_recv', net_io.bytes_recv)
            
            # 进程数
            process_count = len(psutil.pids())
            self.collector.record('system.process.count', process_count)
            
        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")

class ApplicationMonitor:
    """应用性能监控器"""
    
    def __init__(self, collector: MetricCollector):
        self.collector = collector
    
    def record_api_request(self, endpoint: str, method: str, 
                          response_time: float, status_code: int) -> None:
        """记录API请求指标"""
        tags = {
            'endpoint': endpoint,
            'method': method,
            'status_code': str(status_code)
        }
        
        self.collector.record('api.response_time_ms', response_time * 1000, tags)
        self.collector.record('api.request_count', 1, tags)
        
        # 记录错误率
        if status_code >= 400:
            self.collector.record('api.error_count', 1, tags)
    
    def record_database_query(self, query_type: str, execution_time: float, 
                            success: bool = True) -> None:
        """记录数据库查询指标"""
        tags = {
            'query_type': query_type,
            'success': str(success)
        }
        
        self.collector.record('db.query_time_ms', execution_time * 1000, tags)
        self.collector.record('db.query_count', 1, tags)
        
        if not success:
            self.collector.record('db.error_count', 1, tags)
    
    def record_image_processing(self, operation: str, processing_time: float, 
                              success: bool = True) -> None:
        """记录图片处理指标"""
        tags = {
            'operation': operation,
            'success': str(success)
        }
        
        self.collector.record('image.processing_time_ms', processing_time * 1000, tags)
        self.collector.record('image.processing_count', 1, tags)
        
        if not success:
            self.collector.record('image.error_count', 1, tags)
    
    def record_cache_operation(self, cache_type: str, operation: str, 
                             hit: bool = None) -> None:
        """记录缓存操作指标"""
        tags = {
            'cache_type': cache_type,
            'operation': operation
        }
        
        self.collector.record('cache.operation_count', 1, tags)
        
        if hit is not None:
            if hit:
                self.collector.record('cache.hit_count', 1, tags)
            else:
                self.collector.record('cache.miss_count', 1, tags)

class AlertManager:
    """告警管理器"""
    
    def __init__(self, collector: MetricCollector):
        self.collector = collector
        self.alerts = {}
        self.alert_rules = []
        self.lock = threading.RLock()
        
        # 默认告警规则
        self._setup_default_rules()
    
    def _setup_default_rules(self) -> None:
        """设置默认告警规则"""
        self.add_rule(
            'high_cpu_usage',
            lambda: self.collector.get_latest_value('system.cpu.usage_percent') or 0 > 80,
            'CPU使用率过高',
            'warning'
        )
        
        self.add_rule(
            'high_memory_usage',
            lambda: self.collector.get_latest_value('system.memory.usage_percent') or 0 > 85,
            '内存使用率过高',
            'warning'
        )
        
        self.add_rule(
            'low_disk_space',
            lambda: self.collector.get_latest_value('system.disk.usage_percent') or 0 > 90,
            '磁盘空间不足',
            'critical'
        )
        
        self.add_rule(
            'high_api_error_rate',
            lambda: self._calculate_error_rate() > 0.1,  # 10%错误率
            'API错误率过高',
            'warning'
        )
    
    def add_rule(self, rule_id: str, condition: Callable[[], bool], 
                message: str, level: str = 'warning') -> None:
        """添加告警规则"""
        self.alert_rules.append({
            'id': rule_id,
            'condition': condition,
            'message': message,
            'level': level
        })
    
    def check_alerts(self) -> List[Alert]:
        """检查告警条件"""
        new_alerts = []
        
        with self.lock:
            for rule in self.alert_rules:
                rule_id = rule['id']
                
                try:
                    if rule['condition']():
                        # 条件满足，触发告警
                        if rule_id not in self.alerts or self.alerts[rule_id].resolved:
                            alert = Alert(
                                id=rule_id,
                                metric_name=rule_id,
                                level=rule['level'],
                                message=rule['message'],
                                timestamp=time.time()
                            )
                            self.alerts[rule_id] = alert
                            new_alerts.append(alert)
                            logger.warning(f"触发告警: {rule['message']}")
                    else:
                        # 条件不满足，解决告警
                        if rule_id in self.alerts and not self.alerts[rule_id].resolved:
                            self.alerts[rule_id].resolved = True
                            self.alerts[rule_id].resolved_at = time.time()
                            logger.info(f"告警已解决: {rule['message']}")
                
                except Exception as e:
                    logger.error(f"检查告警规则 {rule_id} 失败: {e}")
        
        return new_alerts
    
    def _calculate_error_rate(self) -> float:
        """计算API错误率"""
        try:
            total_requests = self.collector.get_average('api.request_count', 300) or 0
            error_requests = self.collector.get_average('api.error_count', 300) or 0
            
            if total_requests == 0:
                return 0
            
            return error_requests / total_requests
        except Exception:
            return 0
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        with self.lock:
            return [alert for alert in self.alerts.values() if not alert.resolved]
    
    def get_all_alerts(self) -> List[Alert]:
        """获取所有告警"""
        with self.lock:
            return list(self.alerts.values())

class MonitoringSystem:
    """监控系统主类"""
    
    def __init__(self):
        self.collector = MetricCollector()
        self.system_monitor = SystemMonitor(self.collector)
        self.app_monitor = ApplicationMonitor(self.collector)
        self.alert_manager = AlertManager(self.collector)
        
        # 定期检查告警
        self.alert_check_thread = None
        self.alert_checking = False
    
    def start(self) -> None:
        """启动监控系统"""
        self.system_monitor.start_monitoring()
        self._start_alert_checking()
        logger.info("监控系统已启动")
    
    def stop(self) -> None:
        """停止监控系统"""
        self.system_monitor.stop_monitoring()
        self._stop_alert_checking()
        logger.info("监控系统已停止")
    
    def _start_alert_checking(self) -> None:
        """开始告警检查"""
        if self.alert_checking:
            return
        
        self.alert_checking = True
        self.alert_check_thread = threading.Thread(target=self._alert_check_loop, daemon=True)
        self.alert_check_thread.start()
    
    def _stop_alert_checking(self) -> None:
        """停止告警检查"""
        self.alert_checking = False
        if self.alert_check_thread:
            self.alert_check_thread.join(timeout=5)
    
    def _alert_check_loop(self) -> None:
        """告警检查循环"""
        while self.alert_checking:
            try:
                self.alert_manager.check_alerts()
                time.sleep(60)  # 每分钟检查一次
            except Exception as e:
                logger.error(f"告警检查失败: {e}")
                time.sleep(60)
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取监控面板数据"""
        return {
            'metrics': self.collector.get_all_metrics(),
            'active_alerts': [alert.to_dict() for alert in self.alert_manager.get_active_alerts()],
            'system_status': self._get_system_status()
        }
    
    def _get_system_status(self) -> Dict[str, str]:
        """获取系统状态"""
        cpu_usage = self.collector.get_latest_value('system.cpu.usage_percent') or 0
        memory_usage = self.collector.get_latest_value('system.memory.usage_percent') or 0
        disk_usage = self.collector.get_latest_value('system.disk.usage_percent') or 0
        
        status = 'healthy'
        if cpu_usage > 80 or memory_usage > 85 or disk_usage > 90:
            status = 'warning'
        if cpu_usage > 95 or memory_usage > 95 or disk_usage > 95:
            status = 'critical'
        
        return {
            'overall': status,
            'cpu': 'critical' if cpu_usage > 95 else 'warning' if cpu_usage > 80 else 'healthy',
            'memory': 'critical' if memory_usage > 95 else 'warning' if memory_usage > 85 else 'healthy',
            'disk': 'critical' if disk_usage > 95 else 'warning' if disk_usage > 90 else 'healthy'
        }

# 创建全局监控系统实例
monitoring_system = MonitoringSystem()
