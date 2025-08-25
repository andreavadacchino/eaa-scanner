"""
Shared dependencies for FastAPI application
Handles authentication, rate limiting, and common dependencies
"""

import os
import time
import jwt
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import HTTPException, Request, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from collections import defaultdict
import hashlib

# ==================== CONFIGURATION ====================

JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Rate limiting configuration
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds

# ==================== AUTHENTICATION ====================

security = HTTPBearer(auto_error=False)

def create_access_token(data: Dict[str, Any]) -> str:
    """
    Create a JWT access token
    
    Args:
        data: Payload data to encode
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[Dict]:
    """
    Verify and decode a JWT token
    
    Args:
        token: JWT token to verify
        
    Returns:
        Decoded payload or None if invalid
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.JWTError:
        return None

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict]:
    """
    Get current authenticated user from JWT token
    
    Args:
        credentials: HTTP Bearer token from request
        
    Returns:
        User data or None if not authenticated
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    payload = verify_token(token)
    
    if not payload:
        return None
    
    # Extract user information from token
    return {
        "id": payload.get("sub"),
        "email": payload.get("email"),
        "can_scan": payload.get("can_scan", True),
        "is_admin": payload.get("is_admin", False)
    }

async def require_auth(
    user: Optional[Dict] = Depends(get_current_user)
) -> Dict:
    """
    Require authenticated user
    
    Args:
        user: Current user from token
        
    Returns:
        User data
        
    Raises:
        HTTPException: If not authenticated
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user

async def require_admin(
    user: Dict = Depends(require_auth)
) -> Dict:
    """
    Require admin user
    
    Args:
        user: Authenticated user
        
    Returns:
        Admin user data
        
    Raises:
        HTTPException: If not admin
    """
    if not user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user

# ==================== RATE LIMITING ====================

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, requests: int = RATE_LIMIT_REQUESTS, window: int = RATE_LIMIT_WINDOW):
        self.requests = requests
        self.window = window
        self.clients = defaultdict(list)
    
    def _clean_old_requests(self, client_id: str, current_time: float):
        """Remove requests outside the time window"""
        cutoff = current_time - self.window
        self.clients[client_id] = [
            req_time for req_time in self.clients[client_id]
            if req_time > cutoff
        ]
    
    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed for client"""
        current_time = time.time()
        self._clean_old_requests(client_id, current_time)
        
        if len(self.clients[client_id]) >= self.requests:
            return False
        
        self.clients[client_id].append(current_time)
        return True
    
    def get_reset_time(self, client_id: str) -> int:
        """Get time until rate limit resets"""
        if not self.clients[client_id]:
            return 0
        
        oldest_request = min(self.clients[client_id])
        reset_time = int(oldest_request + self.window - time.time())
        return max(0, reset_time)

# Global rate limiter instance
rate_limiter = RateLimiter()

def get_client_id(request: Request) -> str:
    """
    Get unique client identifier from request
    
    Args:
        request: FastAPI request object
        
    Returns:
        Client identifier string
    """
    # Try to get real IP from proxy headers
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"
    
    # Add user agent for better identification
    user_agent = request.headers.get("User-Agent", "")
    
    # Create hash for privacy
    identifier = f"{client_ip}:{user_agent}"
    return hashlib.sha256(identifier.encode()).hexdigest()[:16]

async def get_rate_limit(request: Request) -> None:
    """
    Check rate limit for request
    
    Args:
        request: FastAPI request object
        
    Raises:
        HTTPException: If rate limit exceeded
    """
    client_id = get_client_id(request)
    
    if not rate_limiter.is_allowed(client_id):
        reset_time = rate_limiter.get_reset_time(client_id)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {reset_time} seconds",
            headers={
                "X-RateLimit-Limit": str(RATE_LIMIT_REQUESTS),
                "X-RateLimit-Window": str(RATE_LIMIT_WINDOW),
                "X-RateLimit-Reset": str(reset_time)
            }
        )

# ==================== API KEY MANAGEMENT ====================

class APIKeyManager:
    """Manage API keys for external services"""
    
    def __init__(self):
        self.keys = {
            "openai": os.getenv("OPENAI_API_KEY"),
            "wave": os.getenv("WAVE_API_KEY"),
            "anthropic": os.getenv("ANTHROPIC_API_KEY")
        }
    
    def get_key(self, service: str) -> Optional[str]:
        """Get API key for service"""
        return self.keys.get(service)
    
    def validate_key(self, service: str, key: str) -> bool:
        """Validate API key format"""
        validators = {
            "openai": lambda k: k.startswith("sk-") and len(k) > 20,
            "wave": lambda k: len(k) > 10,
            "anthropic": lambda k: k.startswith("sk-ant-") and len(k) > 20
        }
        
        validator = validators.get(service)
        if not validator:
            return False
        
        return validator(key)
    
    def mask_key(self, key: str) -> str:
        """Mask API key for logging"""
        if not key or len(key) < 8:
            return "***"
        return f"{key[:4]}...{key[-4:]}"

# Global API key manager
api_key_manager = APIKeyManager()

async def get_api_key_manager() -> APIKeyManager:
    """Get API key manager instance"""
    return api_key_manager

# ==================== REQUEST VALIDATION ====================

async def validate_url(url: str) -> bool:
    """
    Validate URL for scanning
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Block private IPs unless explicitly allowed
    allow_private = os.getenv("ALLOW_PRIVATE_IPS", "false").lower() == "true"
    
    if not allow_private:
        private_patterns = [
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "192.168.",
            "10.",
            "172.16.",
            "172.17.",
            "172.18.",
            "172.19.",
            "172.20.",
            "172.21.",
            "172.22.",
            "172.23.",
            "172.24.",
            "172.25.",
            "172.26.",
            "172.27.",
            "172.28.",
            "172.29.",
            "172.30.",
            "172.31.",
            "::1",
            "fc00:",
            "fd00:"
        ]
        
        for pattern in private_patterns:
            if pattern in url.lower():
                return False
    
    return True

# ==================== DATABASE SESSION ====================

async def get_db_session():
    """
    Get database session (placeholder for future implementation)
    
    Returns:
        Database session
    """
    # Placeholder for database session management
    # Will be implemented when migrating from file-based storage
    return None

# ==================== CACHING ====================

class SimpleCache:
    """Simple in-memory cache with TTL"""
    
    def __init__(self, default_ttl: int = 300):
        self.cache = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self.cache:
            value, expiry = self.cache[key]
            if time.time() < expiry:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache with TTL"""
        ttl = ttl or self.default_ttl
        expiry = time.time() + ttl
        self.cache[key] = (value, expiry)
    
    def delete(self, key: str):
        """Delete value from cache"""
        if key in self.cache:
            del self.cache[key]
    
    def clear(self):
        """Clear entire cache"""
        self.cache.clear()
    
    def cleanup(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = [
            key for key, (_, expiry) in self.cache.items()
            if expiry < current_time
        ]
        for key in expired_keys:
            del self.cache[key]

# Global cache instance
cache = SimpleCache()

async def get_cache() -> SimpleCache:
    """Get cache instance"""
    return cache

# ==================== BACKGROUND TASKS ====================

class TaskQueue:
    """Simple async task queue"""
    
    def __init__(self):
        self.tasks = []
        self.running = []
        self.completed = []
        self.failed = []
    
    async def add_task(self, task_id: str, coro):
        """Add task to queue"""
        self.tasks.append({
            "id": task_id,
            "coroutine": coro,
            "created_at": datetime.now()
        })
    
    async def get_status(self, task_id: str) -> Optional[str]:
        """Get task status"""
        for task in self.tasks:
            if task["id"] == task_id:
                return "queued"
        
        for task in self.running:
            if task["id"] == task_id:
                return "running"
        
        for task in self.completed:
            if task["id"] == task_id:
                return "completed"
        
        for task in self.failed:
            if task["id"] == task_id:
                return "failed"
        
        return None

# Global task queue
task_queue = TaskQueue()

async def get_task_queue() -> TaskQueue:
    """Get task queue instance"""
    return task_queue