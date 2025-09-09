"""
Advanced Performance Monitoring System for Agno WorkSphere
Real-time metrics collection, analysis, and alerting for production environments
"""

import time
import asyncio
import psutil
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
import logging
from dataclasses import dataclass, asdict
import threading

logger = logging.getLogger(__name__)

@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: float
    value: float
    tags: Dict[str, str] = None

@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot"""
    timestamp: float
    
    # API Metrics
    request_count: int
    avg_response_time: float
    error_rate: float
    requests_per_second: float
    
    # Database Metrics
    db_connections_active: int
    db_connections_idle: int
    db_query_avg_time: float
    db_pool_utilization: float
    
    # Cache Metrics
    cache_hit_rate: float
    cache_miss_rate: float
    cache_size: int
    cache_memory_usage: float
    
    # System Metrics
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, float]
    
    # Application Metrics
    active_users: int
    concurrent_requests: int
    queue_size: int

class PerformanceMonitor:
    """Advanced performance monitoring system"""
    
    def __init__(self, retention_hours: int = 24):
        self.retention_hours = retention_hours
        self.metrics_history: deque = deque(maxlen=retention_hours * 60)  # 1 minute intervals
        self.request_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.alert_thresholds = self._default_thresholds()
        self.is_monitoring = False
        self.monitor_task = None
        
        # Real-time counters
        self.request_counter = 0
        self.error_counter = 0
        self.response_times = deque(maxlen=1000)
        self.active_requests = 0
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Lock for thread safety
        self._lock = threading.Lock()
    
    def _default_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Default alert thresholds"""
        return {
            "response_time": {"warning": 1000, "critical": 3000},  # milliseconds
            "error_rate": {"warning": 0.05, "critical": 0.10},     # 5% warning, 10% critical
            "cpu_usage": {"warning": 70, "critical": 90},          # percentage
            "memory_usage": {"warning": 80, "critical": 95},       # percentage
            "db_pool_utilization": {"warning": 80, "critical": 95}, # percentage
            "cache_hit_rate": {"warning": 0.80, "critical": 0.60}, # 80% warning, 60% critical
            "requests_per_second": {"warning": 100, "critical": 200}
        }
    
    async def start_monitoring(self):
        """Start the monitoring system"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Performance monitoring started")
    
    async def stop_monitoring(self):
        """Stop the monitoring system"""
        self.is_monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Performance monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                metrics = await self._collect_metrics()
                self._store_metrics(metrics)
                await self._check_alerts(metrics)
                await asyncio.sleep(60)  # Collect metrics every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(60)
    
    async def _collect_metrics(self) -> PerformanceMetrics:
        """Collect comprehensive performance metrics"""
        timestamp = time.time()
        
        # Calculate API metrics
        with self._lock:
            request_count = self.request_counter
            error_count = self.error_counter
            response_times_list = list(self.response_times)
            active_requests = self.active_requests
            cache_hits = self.cache_hits
            cache_misses = self.cache_misses
        
        avg_response_time = sum(response_times_list) / len(response_times_list) if response_times_list else 0
        error_rate = error_count / max(request_count, 1)
        requests_per_second = request_count / 60  # Requests in last minute
        
        # Cache metrics
        total_cache_requests = cache_hits + cache_misses
        cache_hit_rate = cache_hits / max(total_cache_requests, 1)
        cache_miss_rate = cache_misses / max(total_cache_requests, 1)
        
        # System metrics
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        network = psutil.net_io_counters()
        
        # Database metrics (mock values - would integrate with actual DB monitoring)
        db_connections_active = 5  # Would get from actual pool
        db_connections_idle = 15   # Would get from actual pool
        db_query_avg_time = 10.5   # Would calculate from query logs
        db_pool_utilization = (db_connections_active / (db_connections_active + db_connections_idle)) * 100
        
        return PerformanceMetrics(
            timestamp=timestamp,
            request_count=request_count,
            avg_response_time=avg_response_time,
            error_rate=error_rate,
            requests_per_second=requests_per_second,
            db_connections_active=db_connections_active,
            db_connections_idle=db_connections_idle,
            db_query_avg_time=db_query_avg_time,
            db_pool_utilization=db_pool_utilization,
            cache_hit_rate=cache_hit_rate,
            cache_miss_rate=cache_miss_rate,
            cache_size=len(self.request_metrics),
            cache_memory_usage=0.0,  # Would calculate actual cache memory usage
            cpu_usage=cpu_usage,
            memory_usage=memory.percent,
            disk_usage=disk.percent,
            network_io={
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv
            },
            active_users=0,  # Would track from session data
            concurrent_requests=active_requests,
            queue_size=0  # Would track from task queue
        )
    
    def _store_metrics(self, metrics: PerformanceMetrics):
        """Store metrics in history"""
        self.metrics_history.append(metrics)
        
        # Reset counters for next interval
        with self._lock:
            self.request_counter = 0
            self.error_counter = 0
            self.response_times.clear()
            self.cache_hits = 0
            self.cache_misses = 0
    
    async def _check_alerts(self, metrics: PerformanceMetrics):
        """Check for alert conditions"""
        alerts = []
        
        # Check each threshold
        checks = [
            ("response_time", metrics.avg_response_time),
            ("error_rate", metrics.error_rate),
            ("cpu_usage", metrics.cpu_usage),
            ("memory_usage", metrics.memory_usage),
            ("db_pool_utilization", metrics.db_pool_utilization),
            ("cache_hit_rate", metrics.cache_hit_rate),
            ("requests_per_second", metrics.requests_per_second)
        ]
        
        for metric_name, value in checks:
            thresholds = self.alert_thresholds.get(metric_name, {})
            
            if value >= thresholds.get("critical", float('inf')):
                alerts.append({
                    "level": "CRITICAL",
                    "metric": metric_name,
                    "value": value,
                    "threshold": thresholds["critical"],
                    "timestamp": metrics.timestamp
                })
            elif value >= thresholds.get("warning", float('inf')):
                alerts.append({
                    "level": "WARNING",
                    "metric": metric_name,
                    "value": value,
                    "threshold": thresholds["warning"],
                    "timestamp": metrics.timestamp
                })
        
        # Special case for cache hit rate (lower is worse)
        if metrics.cache_hit_rate <= self.alert_thresholds["cache_hit_rate"]["critical"]:
            alerts.append({
                "level": "CRITICAL",
                "metric": "cache_hit_rate",
                "value": metrics.cache_hit_rate,
                "threshold": self.alert_thresholds["cache_hit_rate"]["critical"],
                "timestamp": metrics.timestamp
            })
        
        if alerts:
            await self._send_alerts(alerts)
    
    async def _send_alerts(self, alerts: List[Dict]):
        """Send alerts (would integrate with alerting system)"""
        for alert in alerts:
            logger.warning(f"ALERT [{alert['level']}]: {alert['metric']} = {alert['value']:.2f} "
                         f"(threshold: {alert['threshold']:.2f})")
    
    def record_request(self, endpoint: str, method: str, response_time: float, status_code: int):
        """Record API request metrics"""
        with self._lock:
            self.request_counter += 1
            self.response_times.append(response_time)
            
            if status_code >= 400:
                self.error_counter += 1
            
            # Store detailed request metrics
            self.request_metrics[f"{method}:{endpoint}"].append({
                "timestamp": time.time(),
                "response_time": response_time,
                "status_code": status_code
            })
    
    def record_cache_hit(self):
        """Record cache hit"""
        with self._lock:
            self.cache_hits += 1
    
    def record_cache_miss(self):
        """Record cache miss"""
        with self._lock:
            self.cache_misses += 1
    
    def increment_active_requests(self):
        """Increment active request counter"""
        with self._lock:
            self.active_requests += 1
    
    def decrement_active_requests(self):
        """Decrement active request counter"""
        with self._lock:
            self.active_requests = max(0, self.active_requests - 1)
    
    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """Get the most recent metrics"""
        return self.metrics_history[-1] if self.metrics_history else None
    
    def get_metrics_history(self, hours: int = 1) -> List[PerformanceMetrics]:
        """Get metrics history for specified hours"""
        cutoff_time = time.time() - (hours * 3600)
        return [m for m in self.metrics_history if m.timestamp >= cutoff_time]
    
    def get_endpoint_stats(self, endpoint: str, method: str = "GET") -> Dict[str, Any]:
        """Get statistics for specific endpoint"""
        key = f"{method}:{endpoint}"
        requests = list(self.request_metrics[key])
        
        if not requests:
            return {"request_count": 0}
        
        response_times = [r["response_time"] for r in requests]
        status_codes = [r["status_code"] for r in requests]
        
        return {
            "request_count": len(requests),
            "avg_response_time": sum(response_times) / len(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "error_rate": len([s for s in status_codes if s >= 400]) / len(status_codes),
            "last_request": max(r["timestamp"] for r in requests)
        }
    
    def export_metrics(self, format: str = "json") -> str:
        """Export metrics in specified format"""
        current_metrics = self.get_current_metrics()
        if not current_metrics:
            return "{}" if format == "json" else ""
        
        if format == "json":
            return json.dumps(asdict(current_metrics), indent=2)
        elif format == "prometheus":
            # Convert to Prometheus format
            metrics_dict = asdict(current_metrics)
            prometheus_lines = []
            for key, value in metrics_dict.items():
                if isinstance(value, (int, float)):
                    prometheus_lines.append(f"agno_worksphere_{key} {value}")
            return "\n".join(prometheus_lines)
        
        return str(current_metrics)

# Global monitor instance
performance_monitor = PerformanceMonitor()

async def init_monitoring():
    """Initialize performance monitoring"""
    await performance_monitor.start_monitoring()

async def stop_monitoring():
    """Stop performance monitoring"""
    await performance_monitor.stop_monitoring()
