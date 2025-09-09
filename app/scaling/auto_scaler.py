"""
Intelligent Auto-Scaling System for Agno WorkSphere
Monitors load patterns and automatically scales resources based on real-world usage
"""

import asyncio
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import statistics

logger = logging.getLogger(__name__)

class ScalingAction(Enum):
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    NO_ACTION = "no_action"

@dataclass
class ScalingDecision:
    """Scaling decision with reasoning"""
    action: ScalingAction
    resource_type: str
    current_value: int
    target_value: int
    reason: str
    confidence: float
    timestamp: float

@dataclass
class LoadPattern:
    """Load pattern analysis"""
    avg_load: float
    peak_load: float
    trend: str  # "increasing", "decreasing", "stable"
    pattern_type: str  # "steady", "spiky", "gradual"
    prediction: float

class ResourceScaler:
    """Intelligent resource scaling system"""
    
    def __init__(self):
        self.scaling_config = self._default_scaling_config()
        self.load_history: List[Dict] = []
        self.scaling_decisions: List[ScalingDecision] = []
        self.is_scaling_enabled = True
        self.cooldown_period = 300  # 5 minutes between scaling actions
        self.last_scaling_action = 0
        
        # Current resource levels
        self.current_resources = {
            "db_connections": 20,
            "cache_size": 1000,
            "worker_processes": 1,
            "memory_limit": 512  # MB
        }
        
        # Resource limits
        self.resource_limits = {
            "db_connections": {"min": 5, "max": 100},
            "cache_size": {"min": 100, "max": 10000},
            "worker_processes": {"min": 1, "max": 8},
            "memory_limit": {"min": 256, "max": 4096}
        }
    
    def _default_scaling_config(self) -> Dict[str, Any]:
        """Default scaling configuration"""
        return {
            "cpu_thresholds": {
                "scale_up": 70,    # Scale up if CPU > 70%
                "scale_down": 30   # Scale down if CPU < 30%
            },
            "memory_thresholds": {
                "scale_up": 80,    # Scale up if memory > 80%
                "scale_down": 40   # Scale down if memory < 40%
            },
            "response_time_thresholds": {
                "scale_up": 1000,  # Scale up if avg response time > 1000ms
                "scale_down": 200  # Scale down if avg response time < 200ms
            },
            "requests_per_second_thresholds": {
                "scale_up": 50,    # Scale up if RPS > 50
                "scale_down": 10   # Scale down if RPS < 10
            },
            "db_pool_thresholds": {
                "scale_up": 80,    # Scale up if pool utilization > 80%
                "scale_down": 30   # Scale down if pool utilization < 30%
            },
            "cache_hit_thresholds": {
                "scale_up": 60,    # Scale up cache if hit rate < 60%
                "scale_down": 95   # Scale down cache if hit rate > 95%
            },
            "scaling_factors": {
                "conservative": 1.2,  # 20% increase/decrease
                "moderate": 1.5,      # 50% increase/decrease
                "aggressive": 2.0     # 100% increase/decrease
            }
        }
    
    async def analyze_load_patterns(self, metrics_history: List[Any]) -> LoadPattern:
        """Analyze load patterns from metrics history"""
        if len(metrics_history) < 5:
            return LoadPattern(0, 0, "stable", "steady", 0)
        
        # Extract key metrics
        cpu_values = [m.cpu_usage for m in metrics_history[-10:]]
        memory_values = [m.memory_usage for m in metrics_history[-10:]]
        response_times = [m.avg_response_time for m in metrics_history[-10:]]
        rps_values = [m.requests_per_second for m in metrics_history[-10:]]
        
        # Calculate averages and trends
        avg_cpu = statistics.mean(cpu_values)
        avg_memory = statistics.mean(memory_values)
        avg_response_time = statistics.mean(response_times)
        avg_rps = statistics.mean(rps_values)
        
        # Calculate overall load score (0-100)
        load_score = (avg_cpu + avg_memory + min(avg_response_time / 10, 100) + min(avg_rps * 2, 100)) / 4
        
        # Determine trend
        recent_load = statistics.mean([cpu_values[-3:], memory_values[-3:]])
        older_load = statistics.mean([cpu_values[:3], memory_values[:3]])
        
        if recent_load > older_load * 1.1:
            trend = "increasing"
        elif recent_load < older_load * 0.9:
            trend = "decreasing"
        else:
            trend = "stable"
        
        # Determine pattern type
        cpu_variance = statistics.variance(cpu_values) if len(cpu_values) > 1 else 0
        if cpu_variance > 400:  # High variance
            pattern_type = "spiky"
        elif trend != "stable":
            pattern_type = "gradual"
        else:
            pattern_type = "steady"
        
        # Simple prediction (next 5 minutes)
        if trend == "increasing":
            prediction = load_score * 1.2
        elif trend == "decreasing":
            prediction = load_score * 0.8
        else:
            prediction = load_score
        
        return LoadPattern(
            avg_load=load_score,
            peak_load=max(cpu_values + memory_values),
            trend=trend,
            pattern_type=pattern_type,
            prediction=min(prediction, 100)
        )
    
    async def make_scaling_decision(self, current_metrics: Any, load_pattern: LoadPattern) -> List[ScalingDecision]:
        """Make intelligent scaling decisions based on metrics and patterns"""
        decisions = []
        timestamp = time.time()
        
        # Check cooldown period
        if timestamp - self.last_scaling_action < self.cooldown_period:
            return decisions
        
        # Database connection scaling
        db_decision = self._decide_db_scaling(current_metrics, load_pattern)
        if db_decision.action != ScalingAction.NO_ACTION:
            decisions.append(db_decision)
        
        # Cache scaling
        cache_decision = self._decide_cache_scaling(current_metrics, load_pattern)
        if cache_decision.action != ScalingAction.NO_ACTION:
            decisions.append(cache_decision)
        
        # Worker process scaling (simulated)
        worker_decision = self._decide_worker_scaling(current_metrics, load_pattern)
        if worker_decision.action != ScalingAction.NO_ACTION:
            decisions.append(worker_decision)
        
        return decisions
    
    def _decide_db_scaling(self, metrics: Any, pattern: LoadPattern) -> ScalingDecision:
        """Decide on database connection pool scaling"""
        current_connections = self.current_resources["db_connections"]
        utilization = metrics.db_pool_utilization
        
        # Scale up conditions
        if (utilization > self.scaling_config["db_pool_thresholds"]["scale_up"] or
            pattern.trend == "increasing" and pattern.avg_load > 60):
            
            factor = self._get_scaling_factor(pattern)
            target = min(int(current_connections * factor), 
                        self.resource_limits["db_connections"]["max"])
            
            if target > current_connections:
                return ScalingDecision(
                    action=ScalingAction.SCALE_UP,
                    resource_type="db_connections",
                    current_value=current_connections,
                    target_value=target,
                    reason=f"High DB utilization ({utilization:.1f}%) or increasing load trend",
                    confidence=0.8 if utilization > 90 else 0.6,
                    timestamp=time.time()
                )
        
        # Scale down conditions
        elif (utilization < self.scaling_config["db_pool_thresholds"]["scale_down"] and
              pattern.trend == "decreasing" and pattern.avg_load < 40):
            
            factor = 1 / self._get_scaling_factor(pattern)
            target = max(int(current_connections * factor),
                        self.resource_limits["db_connections"]["min"])
            
            if target < current_connections:
                return ScalingDecision(
                    action=ScalingAction.SCALE_DOWN,
                    resource_type="db_connections",
                    current_value=current_connections,
                    target_value=target,
                    reason=f"Low DB utilization ({utilization:.1f}%) and decreasing load",
                    confidence=0.7,
                    timestamp=time.time()
                )
        
        return ScalingDecision(ScalingAction.NO_ACTION, "db_connections", current_connections, 
                             current_connections, "No scaling needed", 0.0, time.time())
    
    def _decide_cache_scaling(self, metrics: Any, pattern: LoadPattern) -> ScalingDecision:
        """Decide on cache scaling"""
        current_cache_size = self.current_resources["cache_size"]
        hit_rate = metrics.cache_hit_rate * 100
        
        # Scale up cache if hit rate is low
        if hit_rate < self.scaling_config["cache_hit_thresholds"]["scale_up"]:
            factor = self._get_scaling_factor(pattern)
            target = min(int(current_cache_size * factor),
                        self.resource_limits["cache_size"]["max"])
            
            if target > current_cache_size:
                return ScalingDecision(
                    action=ScalingAction.SCALE_UP,
                    resource_type="cache_size",
                    current_value=current_cache_size,
                    target_value=target,
                    reason=f"Low cache hit rate ({hit_rate:.1f}%)",
                    confidence=0.9 if hit_rate < 50 else 0.7,
                    timestamp=time.time()
                )
        
        # Scale down cache if hit rate is very high and load is low
        elif (hit_rate > self.scaling_config["cache_hit_thresholds"]["scale_down"] and
              pattern.avg_load < 30):
            
            factor = 1 / self._get_scaling_factor(pattern)
            target = max(int(current_cache_size * factor),
                        self.resource_limits["cache_size"]["min"])
            
            if target < current_cache_size:
                return ScalingDecision(
                    action=ScalingAction.SCALE_DOWN,
                    resource_type="cache_size",
                    current_value=current_cache_size,
                    target_value=target,
                    reason=f"Very high cache hit rate ({hit_rate:.1f}%) and low load",
                    confidence=0.6,
                    timestamp=time.time()
                )
        
        return ScalingDecision(ScalingAction.NO_ACTION, "cache_size", current_cache_size,
                             current_cache_size, "No scaling needed", 0.0, time.time())
    
    def _decide_worker_scaling(self, metrics: Any, pattern: LoadPattern) -> ScalingDecision:
        """Decide on worker process scaling"""
        current_workers = self.current_resources["worker_processes"]
        cpu_usage = metrics.cpu_usage
        response_time = metrics.avg_response_time
        
        # Scale up workers if high CPU or slow response times
        if (cpu_usage > self.scaling_config["cpu_thresholds"]["scale_up"] or
            response_time > self.scaling_config["response_time_thresholds"]["scale_up"]):
            
            target = min(current_workers + 1, self.resource_limits["worker_processes"]["max"])
            
            if target > current_workers:
                return ScalingDecision(
                    action=ScalingAction.SCALE_UP,
                    resource_type="worker_processes",
                    current_value=current_workers,
                    target_value=target,
                    reason=f"High CPU ({cpu_usage:.1f}%) or slow response time ({response_time:.1f}ms)",
                    confidence=0.8,
                    timestamp=time.time()
                )
        
        # Scale down workers if low CPU and fast response times
        elif (cpu_usage < self.scaling_config["cpu_thresholds"]["scale_down"] and
              response_time < self.scaling_config["response_time_thresholds"]["scale_down"] and
              current_workers > 1):
            
            target = max(current_workers - 1, self.resource_limits["worker_processes"]["min"])
            
            if target < current_workers:
                return ScalingDecision(
                    action=ScalingAction.SCALE_DOWN,
                    resource_type="worker_processes",
                    current_value=current_workers,
                    target_value=target,
                    reason=f"Low CPU ({cpu_usage:.1f}%) and fast response time ({response_time:.1f}ms)",
                    confidence=0.7,
                    timestamp=time.time()
                )
        
        return ScalingDecision(ScalingAction.NO_ACTION, "worker_processes", current_workers,
                             current_workers, "No scaling needed", 0.0, time.time())
    
    def _get_scaling_factor(self, pattern: LoadPattern) -> float:
        """Get scaling factor based on load pattern"""
        if pattern.pattern_type == "spiky":
            return self.scaling_config["scaling_factors"]["aggressive"]
        elif pattern.avg_load > 80:
            return self.scaling_config["scaling_factors"]["moderate"]
        else:
            return self.scaling_config["scaling_factors"]["conservative"]
    
    async def execute_scaling_decisions(self, decisions: List[ScalingDecision]) -> List[Dict[str, Any]]:
        """Execute scaling decisions"""
        results = []
        
        for decision in decisions:
            if not self.is_scaling_enabled:
                results.append({
                    "decision": decision,
                    "executed": False,
                    "reason": "Scaling disabled"
                })
                continue
            
            try:
                success = await self._execute_scaling_action(decision)
                results.append({
                    "decision": decision,
                    "executed": success,
                    "reason": "Success" if success else "Failed to execute"
                })
                
                if success:
                    self.last_scaling_action = time.time()
                    self.scaling_decisions.append(decision)
                    logger.info(f"Scaling executed: {decision.resource_type} "
                              f"{decision.action.value} from {decision.current_value} "
                              f"to {decision.target_value}")
                
            except Exception as e:
                logger.error(f"Scaling execution error: {e}")
                results.append({
                    "decision": decision,
                    "executed": False,
                    "reason": f"Error: {str(e)}"
                })
        
        return results
    
    async def _execute_scaling_action(self, decision: ScalingDecision) -> bool:
        """Execute individual scaling action"""
        resource_type = decision.resource_type
        target_value = decision.target_value
        
        # Update current resources (in production, this would trigger actual scaling)
        self.current_resources[resource_type] = target_value
        
        # Simulate scaling actions
        if resource_type == "db_connections":
            logger.info(f"Scaling database connection pool to {target_value}")
            # In production: await db_pool.resize(target_value)
            
        elif resource_type == "cache_size":
            logger.info(f"Scaling cache size to {target_value}")
            # In production: await cache.resize(target_value)
            
        elif resource_type == "worker_processes":
            logger.info(f"Scaling worker processes to {target_value}")
            # In production: trigger container/process scaling
            
        return True
    
    def get_scaling_recommendations(self, metrics: Any, pattern: LoadPattern) -> Dict[str, Any]:
        """Get scaling recommendations without executing"""
        recommendations = {
            "timestamp": time.time(),
            "load_pattern": {
                "avg_load": pattern.avg_load,
                "trend": pattern.trend,
                "pattern_type": pattern.pattern_type,
                "prediction": pattern.prediction
            },
            "current_resources": self.current_resources.copy(),
            "recommendations": []
        }
        
        # Analyze each resource type
        for resource_type in self.current_resources:
            current = self.current_resources[resource_type]
            limits = self.resource_limits[resource_type]
            
            recommendation = {
                "resource": resource_type,
                "current": current,
                "min_limit": limits["min"],
                "max_limit": limits["max"],
                "utilization": self._calculate_utilization(resource_type, metrics),
                "recommendation": "maintain"
            }
            
            # Add specific recommendations based on metrics
            if resource_type == "db_connections" and metrics.db_pool_utilization > 80:
                recommendation["recommendation"] = "scale_up"
                recommendation["reason"] = f"High DB utilization ({metrics.db_pool_utilization:.1f}%)"
            elif resource_type == "cache_size" and metrics.cache_hit_rate < 0.7:
                recommendation["recommendation"] = "scale_up"
                recommendation["reason"] = f"Low cache hit rate ({metrics.cache_hit_rate:.1%})"
            
            recommendations["recommendations"].append(recommendation)
        
        return recommendations
    
    def _calculate_utilization(self, resource_type: str, metrics: Any) -> float:
        """Calculate resource utilization percentage"""
        if resource_type == "db_connections":
            return metrics.db_pool_utilization
        elif resource_type == "cache_size":
            return (1 - metrics.cache_hit_rate) * 100  # Lower hit rate = higher utilization need
        elif resource_type == "worker_processes":
            return metrics.cpu_usage
        else:
            return 0.0
    
    def get_scaling_history(self, hours: int = 24) -> List[ScalingDecision]:
        """Get scaling decision history"""
        cutoff_time = time.time() - (hours * 3600)
        return [d for d in self.scaling_decisions if d.timestamp >= cutoff_time]

# Global scaler instance
auto_scaler = ResourceScaler()
