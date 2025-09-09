"""
Simple rate limiting middleware for production security
"""
import time
from collections import defaultdict, deque
from typing import Dict, Tuple
from fastapi import HTTPException, Request
from app.config import settings


class RateLimiter:
    """Simple in-memory rate limiter with sliding window"""
    
    def __init__(self):
        # Store requests per client IP and endpoint
        self.requests: Dict[str, deque] = defaultdict(lambda: deque())
        self.blocked_ips: Dict[str, float] = {}  # IP -> unblock_time
        
        # Rate limits per endpoint type
        self.limits = {
            'auth_login': {'requests': 5, 'window': 300},      # 5 requests per 5 minutes
            'auth_register': {'requests': 3, 'window': 3600},   # 3 requests per hour
            'general': {'requests': 100, 'window': 60},         # 100 requests per minute
            'upload': {'requests': 20, 'window': 60},           # 20 uploads per minute
        }
    
    def _get_client_key(self, request: Request, endpoint_type: str) -> str:
        """Generate unique key for client and endpoint"""
        # Use X-Forwarded-For if behind proxy, otherwise client IP
        client_ip = request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
        if not client_ip:
            client_ip = request.client.host if request.client else 'unknown'
        
        return f"{client_ip}:{endpoint_type}"
    
    def _get_endpoint_type(self, path: str) -> str:
        """Determine endpoint type for rate limiting"""
        if '/auth/login' in path:
            return 'auth_login'
        elif '/auth/register' in path:
            return 'auth_register'
        elif '/upload' in path:
            return 'upload'
        else:
            return 'general'
    
    def _cleanup_old_requests(self, client_key: str, window: int):
        """Remove requests outside the time window"""
        current_time = time.time()
        requests = self.requests[client_key]
        
        # Remove old requests
        while requests and current_time - requests[0] > window:
            requests.popleft()
    
    def _is_ip_blocked(self, client_ip: str) -> bool:
        """Check if IP is temporarily blocked"""
        if client_ip in self.blocked_ips:
            if time.time() < self.blocked_ips[client_ip]:
                return True
            else:
                # Unblock expired IPs
                del self.blocked_ips[client_ip]
        return False
    
    def _block_ip(self, client_ip: str, duration: int = 3600):
        """Temporarily block an IP address"""
        self.blocked_ips[client_ip] = time.time() + duration
    
    def check_rate_limit(self, request: Request) -> Tuple[bool, Dict]:
        """
        Check if request should be rate limited
        
        Returns:
            (allowed: bool, info: dict)
        """
        endpoint_type = self._get_endpoint_type(request.url.path)
        client_key = self._get_client_key(request, endpoint_type)
        client_ip = client_key.split(':')[0]
        
        # Check if IP is blocked
        if self._is_ip_blocked(client_ip):
            return False, {
                'error': 'IP temporarily blocked',
                'retry_after': int(self.blocked_ips[client_ip] - time.time())
            }
        
        # Get rate limit config
        limit_config = self.limits.get(endpoint_type, self.limits['general'])
        max_requests = limit_config['requests']
        window = limit_config['window']
        
        # Clean up old requests
        self._cleanup_old_requests(client_key, window)
        
        # Check current request count
        current_requests = len(self.requests[client_key])
        
        if current_requests >= max_requests:
            # Block IP if too many auth failures
            if endpoint_type in ['auth_login', 'auth_register']:
                self._block_ip(client_ip, 3600)  # Block for 1 hour
            
            return False, {
                'error': 'Rate limit exceeded',
                'limit': max_requests,
                'window': window,
                'retry_after': window
            }
        
        # Add current request
        self.requests[client_key].append(time.time())
        
        return True, {
            'requests_remaining': max_requests - current_requests - 1,
            'reset_time': int(time.time() + window)
        }


# Global rate limiter instance
rate_limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    
    # Skip rate limiting for health checks and docs
    skip_paths = ['/api/v1/healthz', '/api/v1/readyz', '/docs', '/redoc', '/openapi.json']
    if any(skip_path in request.url.path for skip_path in skip_paths):
        return await call_next(request)
    
    # Check rate limit
    allowed, info = rate_limiter.check_rate_limit(request)
    
    if not allowed:
        # Return 429 Too Many Requests
        raise HTTPException(
            status_code=429,
            detail={
                'error': info.get('error', 'Rate limit exceeded'),
                'message': 'Too many requests. Please try again later.',
                'retry_after': info.get('retry_after', 60)
            },
            headers={'Retry-After': str(info.get('retry_after', 60))}
        )
    
    # Add rate limit headers to response
    response = await call_next(request)
    
    if 'requests_remaining' in info:
        response.headers['X-RateLimit-Remaining'] = str(info['requests_remaining'])
        response.headers['X-RateLimit-Reset'] = str(info['reset_time'])
    
    return response


def get_rate_limit_status() -> Dict:
    """Get current rate limiting statistics"""
    current_time = time.time()
    
    # Count active clients per endpoint type
    active_clients = defaultdict(int)
    total_requests = 0
    
    for client_key, requests in rate_limiter.requests.items():
        if requests:  # Has recent requests
            endpoint_type = client_key.split(':')[1]
            active_clients[endpoint_type] += 1
            total_requests += len(requests)
    
    # Count blocked IPs
    blocked_ips = sum(1 for unblock_time in rate_limiter.blocked_ips.values() 
                     if unblock_time > current_time)
    
    return {
        'active_clients': dict(active_clients),
        'total_active_requests': total_requests,
        'blocked_ips': blocked_ips,
        'rate_limits': rate_limiter.limits
    }
