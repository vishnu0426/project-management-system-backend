#!/usr/bin/env python3
"""
Comprehensive Monitoring and Observability System
Provides metrics collection, health checks, performance tracking, and alerting
"""
import time
import psutil
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
import structlog
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from app.config import settings

logger = structlog.get_logger()

# Prometheus metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])
ACTIVE_CONNECTIONS = Gauge('active_connections', 'Number of active connections')
DATABASE_CONNECTIONS = Gauge('database_connections_active', 'Active database connections')
CACHE_OPERATIONS = Counter('cache_operations_total', 'Total cache operations', ['operation', 'status'])
ERROR_COUNT = Counter('errors_total', 'Total errors', ['error_type', 'endpoint'])

# System metrics
CPU_USAGE = Gauge('cpu_usage_percent', 'CPU usage percentage')
MEMORY_USAGE = Gauge('memory_usage_percent', 'Memory usage percentage')
DISK_USAGE = Gauge('disk_usage_percent', 'Disk usage percentage')

class MetricsCollector:
    """Collects and manages application metrics"""
    
    def __init__(self):
        self.request_times = deque(maxlen=1000)  # Keep last 1000 request times
        self.error_counts = defaultdict(int)
        self.endpoint_stats = defaultdict(lambda: {"count": 0, "total_time": 0, "errors": 0})
        self.start_time = time.time()
        
    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record request metrics"""
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=str(status_code)).inc()
        REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
        
        self.request_times.append(duration)
        self.endpoint_stats[endpoint]["count"] += 1
        self.endpoint_stats[endpoint]["total_time"] += duration
        
        if status_code >= 400:
            self.endpoint_stats[endpoint]["errors"] += 1
            ERROR_COUNT.labels(error_type=f"http_{status_code}", endpoint=endpoint).inc()
    
    def record_cache_operation(self, operation: str, success: bool):
        """Record cache operation metrics"""
        status = "success" if success else "error"
        CACHE_OPERATIONS.labels(operation=operation, status=status).inc()
    
    def get_request_stats(self) -> Dict[str, Any]:
        """Get request statistics"""
        if not self.request_times:
            return {"avg_response_time": 0, "total_requests": 0}
        
        avg_time = sum(self.request_times) / len(self.request_times)
        total_requests = sum(stats["count"] for stats in self.endpoint_stats.values())
        
        return {
            "avg_response_time": round(avg_time, 3),
            "total_requests": total_requests,
            "uptime_seconds": time.time() - self.start_time,
            "endpoints": dict(self.endpoint_stats)
        }

class HealthChecker:
    """Comprehensive health checking system"""
    
    def __init__(self):
        self.checks = {}
        self.last_check_time = {}
        self.check_results = {}
        
    def register_check(self, name: str, check_func, interval: int = 30):
        """Register a health check"""
        self.checks[name] = {"func": check_func, "interval": interval}
        self.last_check_time[name] = 0
        self.check_results[name] = {"status": "unknown", "last_check": None}
    
    async def run_check(self, name: str) -> Dict[str, Any]:
        """Run a specific health check"""
        if name not in self.checks:
            return {"status": "error", "message": "Check not found"}
        
        try:
            start_time = time.time()
            result = await self.checks[name]["func"]()
            check_time = time.time() - start_time
            
            self.check_results[name] = {
                "status": result.get("status", "unknown"),
                "last_check": datetime.utcnow().isoformat(),
                "check_time": round(check_time, 3),
                "details": result
            }
            
            return self.check_results[name]
            
        except Exception as e:
            error_result = {
                "status": "error",
                "last_check": datetime.utcnow().isoformat(),
                "error": str(e)
            }
            self.check_results[name] = error_result
            return error_result
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all registered health checks"""
        current_time = time.time()
        results = {}
        
        for name, check_config in self.checks.items():
            # Check if it's time to run this check
            if current_time - self.last_check_time[name] >= check_config["interval"]:
                results[name] = await self.run_check(name)
                self.last_check_time[name] = current_time
            else:
                # Use cached result
                results[name] = self.check_results.get(name, {"status": "pending"})
        
        # Calculate overall health
        statuses = [result.get("status") for result in results.values()]
        if "error" in statuses:
            overall_status = "unhealthy"
        elif "degraded" in statuses:
            overall_status = "degraded"
        elif all(status == "healthy" for status in statuses):
            overall_status = "healthy"
        else:
            overall_status = "unknown"
        
        return {
            "overall_status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": results
        }

class SystemMonitor:
    """System resource monitoring"""
    
    @staticmethod
    def get_system_metrics() -> Dict[str, Any]:
        """Get current system metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            CPU_USAGE.set(cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            MEMORY_USAGE.set(memory_percent)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            DISK_USAGE.set(disk_percent)
            
            # Network stats
            network = psutil.net_io_counters()
            
            return {
                "cpu": {
                    "usage_percent": cpu_percent,
                    "count": psutil.cpu_count()
                },
                "memory": {
                    "usage_percent": memory_percent,
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2)
                },
                "disk": {
                    "usage_percent": disk_percent,
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2)
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                }
            }
            
        except Exception as e:
            logger.error("Failed to get system metrics", error=str(e))
            return {"error": str(e)}

class AlertManager:
    """Alert management system"""
    
    def __init__(self):
        self.alert_rules = []
        self.active_alerts = {}
        
    def add_alert_rule(self, name: str, condition_func, severity: str = "warning", 
                      cooldown: int = 300):
        """Add an alert rule"""
        self.alert_rules.append({
            "name": name,
            "condition": condition_func,
            "severity": severity,
            "cooldown": cooldown
        })
    
    async def check_alerts(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check all alert rules against current metrics"""
        current_time = time.time()
        new_alerts = []
        
        for rule in self.alert_rules:
            try:
                if await rule["condition"](metrics):
                    alert_key = rule["name"]
                    
                    # Check cooldown
                    if (alert_key not in self.active_alerts or 
                        current_time - self.active_alerts[alert_key]["last_fired"] > rule["cooldown"]):
                        
                        alert = {
                            "name": rule["name"],
                            "severity": rule["severity"],
                            "timestamp": datetime.utcnow().isoformat(),
                            "metrics": metrics
                        }
                        
                        self.active_alerts[alert_key] = {
                            "alert": alert,
                            "last_fired": current_time
                        }
                        
                        new_alerts.append(alert)
                        
                        logger.warning("Alert triggered", alert=alert)
                        
            except Exception as e:
                logger.error("Alert rule evaluation failed", rule=rule["name"], error=str(e))
        
        return new_alerts

# Global instances
metrics_collector = MetricsCollector()
health_checker = HealthChecker()
system_monitor = SystemMonitor()
alert_manager = AlertManager()

# Middleware for request monitoring
async def monitoring_middleware(request: Request, call_next):
    """Middleware to monitor requests"""
    start_time = time.time()
    
    # Extract endpoint pattern
    endpoint = request.url.path
    method = request.method
    
    try:
        response = await call_next(request)
        status_code = response.status_code
        
    except Exception as e:
        status_code = 500
        logger.error("Request failed", endpoint=endpoint, error=str(e))
        raise
    
    finally:
        duration = time.time() - start_time
        metrics_collector.record_request(method, endpoint, status_code, duration)
    
    return response

# Health check functions
async def database_health_check():
    """Database health check"""
    from app.database import db_pool
    return await db_pool.health_check()

async def cache_health_check():
    """Cache health check"""
    from app.cache import cache_manager
    return await cache_manager.health_check()

async def system_health_check():
    """System resource health check"""
    metrics = system_monitor.get_system_metrics()
    
    # Define thresholds
    cpu_threshold = 80
    memory_threshold = 85
    disk_threshold = 90
    
    warnings = []
    if metrics.get("cpu", {}).get("usage_percent", 0) > cpu_threshold:
        warnings.append(f"High CPU usage: {metrics['cpu']['usage_percent']}%")
    
    if metrics.get("memory", {}).get("usage_percent", 0) > memory_threshold:
        warnings.append(f"High memory usage: {metrics['memory']['usage_percent']}%")
    
    if metrics.get("disk", {}).get("usage_percent", 0) > disk_threshold:
        warnings.append(f"High disk usage: {metrics['disk']['usage_percent']}%")
    
    status = "healthy"
    if warnings:
        status = "degraded" if len(warnings) <= 2 else "unhealthy"
    
    return {
        "status": status,
        "metrics": metrics,
        "warnings": warnings
    }

# Initialize health checks
health_checker.register_check("database", database_health_check, interval=30)
health_checker.register_check("cache", cache_health_check, interval=60)
health_checker.register_check("system", system_health_check, interval=30)

# Initialize alert rules
async def high_error_rate_alert(metrics):
    """Alert for high error rate"""
    stats = metrics_collector.get_request_stats()
    total_requests = stats.get("total_requests", 0)
    if total_requests < 10:  # Not enough data
        return False
    
    error_count = sum(
        endpoint_data.get("errors", 0) 
        for endpoint_data in stats.get("endpoints", {}).values()
    )
    error_rate = (error_count / total_requests) * 100
    return error_rate > 5  # Alert if error rate > 5%

async def high_response_time_alert(metrics):
    """Alert for high response time"""
    stats = metrics_collector.get_request_stats()
    avg_response_time = stats.get("avg_response_time", 0)
    return avg_response_time > 2.0  # Alert if avg response time > 2 seconds

async def high_cpu_usage_alert(metrics):
    """Alert for high CPU usage"""
    system_metrics = system_monitor.get_system_metrics()
    cpu_usage = system_metrics.get("cpu", {}).get("usage_percent", 0)
    return cpu_usage > 85

alert_manager.add_alert_rule("high_error_rate", high_error_rate_alert, "critical", 300)
alert_manager.add_alert_rule("high_response_time", high_response_time_alert, "warning", 180)
alert_manager.add_alert_rule("high_cpu_usage", high_cpu_usage_alert, "warning", 300)

# Metrics endpoint
async def get_prometheus_metrics():
    """Get Prometheus metrics"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
