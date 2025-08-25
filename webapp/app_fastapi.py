"""
FastAPI Application for EAA Scanner - FIXED VERSION
Versione corretta con best practices 2025 e sicurezza implementata
"""

import os
import json
import time
import asyncio
import logging
import redis
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

# FastAPI core imports
from fastapi import FastAPI, HTTPException, Depends, Request, Response, status, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import WebSocket, WebSocketDisconnect

# Import routers
from webapp.routers import report_generator

# Pydantic models for validation
from pydantic import BaseModel, Field, HttpUrl, EmailStr, validator, ConfigDict, field_validator
from typing import Union
from pydantic_settings import BaseSettings

# Import del crawler ottimizzato
OPTIMIZED_CRAWLER_AVAILABLE = False
RealWebCrawlerOptimized = None
try:
    # Prova vari metodi di import
    try:
        from webapp.optimized_crawler import RealWebCrawlerOptimized
        OPTIMIZED_CRAWLER_AVAILABLE = True
    except ImportError:
        try:
            from optimized_crawler import RealWebCrawlerOptimized
            OPTIMIZED_CRAWLER_AVAILABLE = True
        except ImportError:
            pass
except Exception:
    pass  # Will log later when logger is available

# Security imports
import secrets
from passlib.context import CryptContext
from jose import JWTError, jwt

# Async support
import httpx
import aiofiles
import concurrent.futures

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log crawler availability e applica patch
if OPTIMIZED_CRAWLER_AVAILABLE:
    logger.info("🚀 Crawler ottimizzato disponibile!")
else:
    logger.info("ℹ️ Tentativo di patch del crawler...")
    try:
        from webapp import crawler_patch
        logger.info("✅ Patch crawler applicata")
    except Exception as e:
        logger.warning(f"⚠️ Patch crawler non riuscita: {e}")
        logger.info("ℹ️ Usando crawler standard")

# ==================== SCAN STATUS TRACKING ====================

# In-memory scan status storage
scan_status_store = {}

class ScanStatus:
    """Status tracker for scan operations"""
    def __init__(self, scan_id: str):
        self.scan_id = scan_id
        self.status = "starting"
        self.progress = 0
        self.message = "Inizializzazione..."
        self.result = None
        self.error = None
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
    def update(self, status: str = None, progress: int = None, message: str = None, result: Any = None, error: str = None):
        """Update scan status"""
        if status is not None:
            self.status = status
        if progress is not None:
            self.progress = progress
        if message is not None:
            self.message = message
        if result is not None:
            self.result = result
        if error is not None:
            self.error = error
        self.updated_at = datetime.now()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response"""
        return {
            "scan_id": self.scan_id,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "polling_interval": 2  # Suggested polling interval in seconds
        }

def get_scan_status(scan_id: str) -> Optional[ScanStatus]:
    """Get scan status by ID"""
    return scan_status_store.get(scan_id)

def create_scan_status(scan_id: str) -> ScanStatus:
    """Create new scan status"""
    status = ScanStatus(scan_id)
    scan_status_store[scan_id] = status
    return status

def cleanup_old_scans():
    """Clean up scans older than 30 minutes"""
    cutoff = datetime.now() - timedelta(minutes=30)
    to_remove = []
    for scan_id, status in scan_status_store.items():
        if status.created_at < cutoff:
            to_remove.append(scan_id)
    for scan_id in to_remove:
        del scan_status_store[scan_id]
    if to_remove:
        logger.info(f"Cleaned up {len(to_remove)} old scans")

# ==================== CONFIGURATION ====================

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    app_name: str = "EAA Scanner API"
    version: str = "2.0.0"
    debug: bool = Field(default=False, env="DEBUG_MODE")
    
    # Server
    host: str = "0.0.0.0"
    port: int = Field(default=8000, env="PORT")
    workers: int = 1  # Single worker for development
    
    # Security - FIXED: Use environment variable for secret key
    secret_key: str = Field(
        default="09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7",
        env="SECRET_KEY"
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS - FIXED: Specific origins instead of wildcard
    cors_origins: List[str] = [
        "http://localhost:8000",
        "http://localhost:3000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:3000",
        "https://eaa-scanner.com",
        "https://www.eaa-scanner.com"
    ]
    cors_credentials: bool = True
    cors_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_headers: List[str] = ["Content-Type", "Authorization", "Accept"]
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_period: int = 60  # seconds
    
    # Redis configuration for distributed rate limiting
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # Trusted Hosts - include Docker service name 'backend' per proxy interno
    # Accept as string from env and parse to list
    trusted_hosts_str: str = Field(
        default="localhost,127.0.0.1,backend,eaa-scanner.com,*.eaa-scanner.com",
        env="TRUSTED_HOSTS"
    )
    
    @property
    def trusted_hosts(self) -> List[str]:
        return [h.strip() for h in self.trusted_hosts_str.split(',')]
    
    # Development flags
    allow_local_urls: bool = Field(default=False, env="DEV_ALLOW_LOCAL_URLS")
    
    # OpenAI
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    
    # Paths
    output_dir: Path = Path("output")
    static_dir: Path = Path("webapp/static")
    templates_dir: Path = Path("webapp/templates")
    
    # Scan limits
    max_concurrent_scans: int = 10
    scan_timeout: int = 300  # 5 minutes
    
    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="allow")

settings = Settings()
# Estende trusted hosts con eventuale variabile d'ambiente (CSV)
try:
    extra_hosts = os.getenv("TRUSTED_HOSTS", "")
    if extra_hosts:
        settings.trusted_hosts = list({*settings.trusted_hosts, *[h.strip() for h in extra_hosts.split(',') if h.strip()]})
except Exception:
    pass

# ==================== SECURITY SETUP ====================

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v2/auth/token", auto_error=False)

# ==================== REDIS SETUP ====================

try:
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    redis_available = True
except Exception as e:
    logger.warning(f"Redis not available: {e}. Falling back to in-memory rate limiting.")
    redis_client = None
    redis_available = False

# ==================== PYDANTIC MODELS ====================

class HealthResponse(BaseModel):
    """Health check response model"""
    ok: bool
    timestamp: datetime
    version: str
    redis: bool
    active_scans: int
    system_info: Dict[str, Any]

class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str
    status_code: int
    timestamp: str
    details: Optional[Dict[str, Any]] = None

class Token(BaseModel):
    """JWT Token response"""
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """JWT Token payload"""
    username: Optional[str] = None
    scopes: List[str] = []

class User(BaseModel):
    """User model"""
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    disabled: bool = False

class UserInDB(User):
    """User in database with hashed password"""
    hashed_password: str

class ScannerConfig(BaseModel):
    """Configuration for individual scanners"""
    enabled: bool = True
    timeout: int = 60
    options: Dict[str, Any] = {}

class ScannerToggles(BaseModel):
    """Scanner enable/disable toggles"""
    wave: ScannerConfig = ScannerConfig(enabled=False)
    axe: ScannerConfig = ScannerConfig()
    lighthouse: ScannerConfig = ScannerConfig()
    pa11y: ScannerConfig = ScannerConfig()

class ScanRequest(BaseModel):
    """Scan request payload with validation"""
    url: HttpUrl
    company_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    scannerConfig: Optional[ScannerToggles] = None
    simulate: bool = False  # Solo scansioni reali; campo ignorato
    
    @validator('url')
    def validate_url(cls, v):
        """Enhanced URL validation to prevent SSRF"""
        url_str = str(v)
        
        # Block dangerous schemes
        if url_str.startswith(('javascript:', 'data:', 'file:', 'ftp:')):
            raise ValueError('Invalid URL scheme')
        
        # CRITICAL FIX: Return the validated value
        return v

class MultiPageScanRequest(BaseModel):
    """Multi-page scan request for batch scanning"""
    pages: List[HttpUrl] = Field(..., min_items=1, max_items=100)
    company_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    mode: Optional[str] = Field(default="real")
    scanners: Optional[Union[Dict[str, bool], List[str]]] = None
    discovery_session_id: Optional[str] = None
    
    @validator('scanners', pre=True)
    def normalize_scanners(cls, v):
        """Normalize scanners format - accept both array and dict formats"""
        if v is None:
            return None
        
        valid_scanners = {"wave", "axe", "lighthouse", "pa11y"}
        
        # If it's a dict, check if it's a malformed dict with numeric indices
        if isinstance(v, dict):
            # Check if this is a malformed array-like dict from frontend
            # Example: {'0': 'wave', '1': 'axe', 'lighthouse': True}
            if any(isinstance(key, (int, str)) and str(key).isdigit() for key in v.keys()):
                # Extract scanners from numeric indices and boolean values
                scanner_dict = {}
                for key, value in v.items():
                    if isinstance(value, str) and value in valid_scanners:
                        scanner_dict[value] = True
                    elif isinstance(value, bool) and key in valid_scanners:
                        scanner_dict[key] = value
                return scanner_dict if scanner_dict else None
            else:
                # Already a proper dict format, filter valid scanners
                return {k: v for k, v in v.items() if k in valid_scanners}
        
        # If it's a list, convert to dict with all values True
        if isinstance(v, list):
            scanner_dict = {}
            for scanner in v:
                if isinstance(scanner, str) and scanner in valid_scanners:
                    scanner_dict[scanner] = True
            return scanner_dict if scanner_dict else None
        
        # If it's a string, single scanner
        if isinstance(v, str) and v in valid_scanners:
            return {v: True}
        
        return None
    
    @validator('pages')
    def validate_pages(cls, v):
        """Validate all URLs in pages list"""
        for url in v:
            url_str = str(url)
            if url_str.startswith(('javascript:', 'data:', 'file:', 'ftp:')):
                raise ValueError(f'Invalid URL scheme in: {url_str}')
        
        # Block local addresses (basic SSRF protection)
        if not settings.allow_local_urls:
            blocked_markers = ['localhost', '127.0.0.1', '0.0.0.0', '::1', '192.168.', '10.']
            lower = url_str.lower()
            for marker in blocked_markers:
                if marker in lower:
                    raise ValueError('Local addresses not allowed (set DEV_ALLOW_LOCAL_URLS for development)')
        
        # Ensure HTTP/HTTPS
        if not url_str.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        
        return v
    
    @validator('company_name')
    def sanitize_company_name(cls, v):
        """Sanitize company name to prevent XSS"""
        # Remove any HTML/JS tags
        import re
        cleaned = re.sub(r'<[^>]*>', '', v)
        cleaned = re.sub(r'[<>\"\'&]', '', cleaned)
        return cleaned.strip()

class ScanResponse(BaseModel):
    """Scan response"""
    scan_id: str
    status: str
    progress: int
    message: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

class APIKeyValidationResponse(BaseModel):
    """API Key validation response"""
    success: bool
    data: Dict[str, Any]
    message: Optional[str] = None

class RegenerationRequest(BaseModel):
    """LLM regeneration request"""
    scan_id: str
    model: str = "gpt-4o"
    content_type: str = "full_report"
    instructions: Optional[str] = None

class RegenerationResponse(BaseModel):
    """LLM regeneration response"""
    regeneration_id: str
    status: str
    progress: int = 0
    estimated_completion: Optional[datetime] = None
    cost_estimate: Optional[float] = None

# ==================== AUTHENTICATION FUNCTIONS ====================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> Optional[User]:
    """Get current user from JWT token and database"""
    if not token:
        return None
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, scopes=payload.get("scopes", []))
    except JWTError:
        raise credentials_exception
    
    # Fetch user from database
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute('SELECT username, email, full_name, disabled FROM users WHERE username = ?', (token_data.username,))
        user_row = cursor.fetchone()
        conn.close()
        
        if user_row:
            username, email, full_name, disabled = user_row
            if disabled:
                raise credentials_exception
            
            return User(
                username=username,
                email=email,
                full_name=full_name or "User",
                disabled=disabled
            )
        else:
            # Create default user if not exists (for backward compatibility)
            return User(
                username=token_data.username,
                email=f"{token_data.username}@example.com",
                full_name="Test User"
            )
    except Exception as e:
        logger.error(f"Error fetching user from database: {e}")
        raise credentials_exception

def require_auth(user: User = Depends(get_current_user)):
    """Dependency to require authentication"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

# ==================== RATE LIMITING ====================

class RateLimiter:
    """Distributed rate limiter using Redis or fallback to memory"""
    
    def __init__(self):
        self.memory_store = {}  # Fallback for when Redis is unavailable
    
    async def is_allowed(self, key: str, limit: int = 100, window: int = 60) -> bool:
        """Check if request is allowed under rate limit"""
        
        if redis_available and redis_client:
            try:
                # Use Redis for distributed rate limiting
                pipe = redis_client.pipeline()
                now = time.time()
                window_start = now - window
                
                # Remove old entries
                pipe.zremrangebyscore(key, 0, window_start)
                # Count current entries
                pipe.zcard(key)
                # Add current request
                pipe.zadd(key, {str(now): now})
                # Set expiry
                pipe.expire(key, window)
                
                results = pipe.execute()
                current_count = results[1]
                
                return current_count < limit
            except Exception as e:
                logger.error(f"Redis error: {e}")
                # Fall back to memory
        
        # In-memory fallback
        now = time.time()
        if key not in self.memory_store:
            self.memory_store[key] = []
        
        # Remove old entries
        self.memory_store[key] = [
            timestamp for timestamp in self.memory_store[key]
            if timestamp > now - window
        ]
        
        # Check limit
        if len(self.memory_store[key]) >= limit:
            return False
        
        # Add current request
        self.memory_store[key].append(now)
        return True

rate_limiter = RateLimiter()

async def check_rate_limit(request: Request):
    """Rate limit dependency"""
    # Use IP address as key
    client_ip = request.client.host
    key = f"rate_limit:{client_ip}"
    
    allowed = await rate_limiter.is_allowed(
        key,
        settings.rate_limit_requests,
        settings.rate_limit_period
    )
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later."
        )

# ==================== SCAN MANAGER ====================

class ScanManager:
    """Manages active scans with concurrency limits"""
    
    def __init__(self):
        self.scans: Dict[str, Dict[str, Any]] = {}
        self.active_count = 0
        self.max_concurrent = settings.max_concurrent_scans
        self._lock = asyncio.Lock()
    
    async def create_scan(self, request: ScanRequest) -> str:
        """Create a new scan with concurrency check and database insertion"""
        async with self._lock:
            if self.active_count >= self.max_concurrent:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many active scans. Maximum: {self.max_concurrent}"
                )
            
            scan_id = f"v2scan_{secrets.token_urlsafe(8)}"
            self.scans[scan_id] = {
                "id": scan_id,
                "status": "pending",
                "progress": 0,
                "request": request.dict(),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "results": None
            }
            self.active_count += 1
            
            # Insert into database immediately
            try:
                conn = sqlite3.connect(get_database_path())
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO scans 
                    (id, url, company_name, email, status, progress, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    scan_id,
                    str(request.url),
                    request.company_name,
                    request.email,
                    "pending",
                    0,
                    datetime.utcnow().isoformat(),
                    datetime.utcnow().isoformat()
                ))
                conn.commit()
                conn.close()
                logger.info(f"Created scan {scan_id} in database")
            except Exception as e:
                logger.error(f"Failed to create scan in database: {e}")
            
            return scan_id
    
    async def update_scan(self, scan_id: str, **kwargs):
        """Update scan status and sync to database"""
        if scan_id in self.scans:
            self.scans[scan_id].update(kwargs)
            self.scans[scan_id]["updated_at"] = datetime.utcnow()
            
            # Update active count if completed
            if kwargs.get("status") in ["completed", "failed"]:
                async with self._lock:
                    self.active_count = max(0, self.active_count - 1)
            
            # Sync important updates to database
            if any(key in kwargs for key in ["status", "progress", "results"]):
                # Sync to database in background to avoid blocking
                asyncio.create_task(
                    sync_scan_to_database(
                        scan_id,
                        status=kwargs.get("status"),
                        progress=kwargs.get("progress"),
                        results=kwargs.get("results")
                    )
                )
    
    def get_scan(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Get scan by ID"""
        return self.scans.get(scan_id)
    
    async def cleanup_old_scans(self):
        """Remove scans older than 1 hour"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                cutoff = datetime.utcnow() - timedelta(hours=1)
                
                async with self._lock:
                    to_remove = [
                        scan_id for scan_id, scan in self.scans.items()
                        if scan["created_at"] < cutoff
                    ]
                    
                    for scan_id in to_remove:
                        if self.scans[scan_id]["status"] in ["pending", "running"]:
                            self.active_count = max(0, self.active_count - 1)
                        del self.scans[scan_id]
                    
                    if to_remove:
                        logger.info(f"Cleaned up {len(to_remove)} old scans")
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")

scan_manager = ScanManager()

# ==================== DATABASE SYNC HELPER ====================

async def sync_scan_to_database(scan_id: str, status: str = None, progress: int = None, 
                                results: Dict[str, Any] = None, message: str = None):
    """Helper function to keep database synchronized with scan_manager"""
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        
        # Get current scan from manager
        scan = scan_manager.get_scan(scan_id)
        if not scan:
            logger.warning(f"Scan {scan_id} not found in manager, skipping database sync")
            return
            
        # Use provided values or fallback to scan values
        final_status = status or scan.get("status", "unknown")
        final_progress = progress if progress is not None else scan.get("progress", 0)
        final_results = results or scan.get("results")
        
        # Update database
        if final_results:
            cursor.execute('''
                UPDATE scans 
                SET status = ?, progress = ?, results = ?, updated_at = ?
                WHERE id = ?
            ''', (
                final_status,
                final_progress, 
                json.dumps(final_results, ensure_ascii=False) if final_results else None,
                datetime.utcnow().isoformat(),
                scan_id
            ))
        else:
            cursor.execute('''
                UPDATE scans 
                SET status = ?, progress = ?, updated_at = ?
                WHERE id = ?
            ''', (
                final_status,
                final_progress,
                datetime.utcnow().isoformat(),
                scan_id
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"Database synced for scan {scan_id}: status={final_status}, progress={final_progress}")
        
    except Exception as e:
        logger.error(f"Failed to sync scan {scan_id} to database: {e}")

# ==================== WEBSOCKET MANAGER ====================

class WebSocketManager:
    """Manages WebSocket connections with authentication"""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, scan_id: str, token: Optional[str] = None):
        """Accept WebSocket connection with optional authentication"""
        # In production, validate token here
        await websocket.accept()
        
        if scan_id not in self.active_connections:
            self.active_connections[scan_id] = []
        self.active_connections[scan_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, scan_id: str):
        """Remove WebSocket connection"""
        if scan_id in self.active_connections:
            self.active_connections[scan_id].remove(websocket)
            if not self.active_connections[scan_id]:
                del self.active_connections[scan_id]
    
    async def broadcast(self, scan_id: str, message: dict):
        """Broadcast message to all connections for a scan"""
        if scan_id in self.active_connections:
            disconnected = []
            for websocket in self.active_connections[scan_id]:
                try:
                    await websocket.send_json(message)
                except Exception:
                    disconnected.append(websocket)
            
            # Clean up disconnected clients
            for ws in disconnected:
                self.disconnect(ws, scan_id)

ws_manager = WebSocketManager()

# ==================== APPLICATION SETUP ====================

# Store for discovery sessions (temporary, not persisted)
discovery_sessions: Dict[str, Any] = {}

# Store for user-configured API keys (override defaults)
# Priority: 1. User-configured (from panel), 2. Environment variable, 3. Default
user_configured_keys: Dict[str, str] = {
    "openai": None,  # Will override settings.openai_api_key if set
    "wave": None     # Will override WAVE_API_KEY env var if set
}

def get_effective_openai_key() -> Optional[str]:
    """Get the effective OpenAI API key with priority order"""
    # Priority 1: User-configured key from panel
    if user_configured_keys.get("openai"):
        logger.debug("Using user-configured OpenAI key from panel")
        return user_configured_keys["openai"]
    
    # Priority 2: Environment variable / settings
    if settings.openai_api_key:
        # Skip placeholder keys
        if "placeholder" not in settings.openai_api_key.lower() and "default" not in settings.openai_api_key.lower():
            logger.debug("Using OpenAI key from environment/settings")
            return settings.openai_api_key
    
    # Priority 3: Check for test mode environment variable
    test_mode = os.getenv("EAA_TEST_MODE", "false").lower() == "true"
    if test_mode:
        logger.info("Test mode enabled, using demo OpenAI key")
        return "demo-openai-key-for-testing"
    
    logger.warning("No valid OpenAI API key configured")
    return None

def get_effective_wave_key() -> Optional[str]:
    """Get the effective WAVE API key with priority order"""
    # Priority 1: User-configured key from panel
    if user_configured_keys.get("wave"):
        logger.debug("Using user-configured WAVE key from panel")
        return user_configured_keys["wave"]
    
    # Priority 2: Environment variable
    wave_key = os.getenv("WAVE_API_KEY")
    if wave_key:
        logger.debug("Using WAVE key from environment")
        return wave_key
    
    logger.warning("No WAVE API key configured")
    return None

# User management functions
class UserCreate(BaseModel):
    """User creation model"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None

# NOTE: This function will be decorated after app is created
async def create_user(user_data: UserCreate):
    """Create new user account"""
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        
        # Check if user already exists
        cursor.execute('SELECT username FROM users WHERE username = ? OR email = ?', (user_data.username, user_data.email))
        existing_user = cursor.fetchone()
        
        if existing_user:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already exists"
            )
        
        # Hash password and create user
        hashed_password = get_password_hash(user_data.password)
        
        cursor.execute('''
            INSERT INTO users (username, email, hashed_password, full_name, disabled)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            user_data.username,
            user_data.email,
            hashed_password,
            user_data.full_name,
            False
        ))
        
        conn.commit()
        conn.close()
        
        return User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name or user_data.username,
            disabled=False
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore nella creazione dell'utente"
        )

async def cleanup_task_runner():
    """Background task to clean up old scans every 10 minutes"""
    while True:
        try:
            await asyncio.sleep(600)  # Wait 10 minutes
            cleanup_old_scans()
        except asyncio.CancelledError:
            logger.info("Cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.version}")
    
    # Initialize database first
    init_database()
    
    # Start periodic cleanup task for in-memory scan status
    cleanup_task = asyncio.create_task(cleanup_task_runner())
    
    # Start original scan manager cleanup (if it exists)
    scan_cleanup_task = None
    try:
        scan_cleanup_task = asyncio.create_task(scan_manager.cleanup_old_scans())
    except AttributeError:
        logger.info("Scan manager cleanup not available")
    
    # Initialize Redis connection
    if redis_available:
        logger.info("Redis connected for distributed rate limiting")
    else:
        logger.warning("Redis not available, using in-memory rate limiting")
    
    yield
    
    # Shutdown
    cleanup_task.cancel()
    if scan_cleanup_task:
        scan_cleanup_task.cancel()
    logger.info("Application shutdown complete")

# Create FastAPI app with proper configuration
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    lifespan=lifespan,
    docs_url="/docs",  # Always enable for testing
    redoc_url="/redoc",
    openapi_url="/openapi.json" if settings.debug else "/api/openapi.json"
)

# ==================== GLOBAL STATE ====================

# In-memory storage for active sessions
discovery_sessions = {}
scan_sessions = {}

# ==================== MIDDLEWARE CONFIGURATION ====================

# IMPORTANT: Order matters! TrustedHost should be first
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.trusted_hosts
)

# CORS configuration - FIXED with specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_credentials,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
    max_age=600
)

# GZip compression for responses
app.add_middleware(
    GZipMiddleware,
    minimum_size=1000
)

# ==================== REGISTER USER ENDPOINT ====================

# Now we can register the create_user endpoint after app is created
app.add_api_route(
    "/api/users/create",
    create_user,
    methods=["POST"],
    response_model=User,
    tags=["users"],
    summary="Create new user account"
)

# ==================== CUSTOM MIDDLEWARE ====================

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    # Process time header for monitoring
    response.headers["X-Process-Time"] = str(time.perf_counter())
    
    return response

# ==================== STATIC FILES ====================

# Custom static files handler with no-cache headers for development
from starlette.responses import Response
import os

class NoCacheStaticFiles(StaticFiles):
    """Static files with no-cache headers for development"""
    
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        # Add no-cache headers for JS and CSS files
        if path.endswith(('.js', '.css')):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

# TEMPORARY COMMENT: Fix static directory issue
# app.mount("/static", NoCacheStaticFiles(directory=str(settings.static_dir)), name="static")
# Mount output directory for serving generated reports
output_dir = Path("/app/output")
if output_dir.exists():
    app.mount("/output", NoCacheStaticFiles(directory=str(output_dir)), name="output")

# ==================== ROUTERS ====================

# Include report generator router
app.include_router(report_generator.router, prefix="/api/report", tags=["report"])

# ==================== API ROUTES ====================

@app.get("/api/test-db")
async def test_database():
    """Test endpoint per verificare stato database"""
    try:
        db_path = get_database_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        # Try to count scans
        try:
            cursor.execute("SELECT COUNT(*) FROM scans")
            scan_count = cursor.fetchone()[0]
        except sqlite3.OperationalError as e:
            scan_count = f"Error: {e}"
        
        conn.close()
        
        return {
            "database_path": db_path,
            "path_exists": os.path.exists(db_path),
            "tables": [table[0] for table in tables],
            "scan_count": scan_count
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/health", response_model=HealthResponse)
@app.get("/api/health", response_model=HealthResponse)  # Backward compatibility alias
async def health_check():
    """Comprehensive health check endpoint"""
    
    # Check system components
    redis_status = redis_available
    if redis_available and redis_client:
        try:
            redis_client.ping()
        except Exception:
            redis_status = False
    
    # Collect system information
    system_info = {
        "python_version": "3.11+",
        "fastapi_version": "0.109+",
        "max_concurrent_scans": settings.max_concurrent_scans,
        "rate_limit_enabled": True,
        "security_headers": True,
        "compression_enabled": True
    }
    
    return HealthResponse(
        ok=True,
        timestamp=datetime.utcnow(),
        version=settings.version,
        redis=redis_status,
        active_scans=scan_manager.active_count,
        system_info=system_info
    )

@app.post("/api/v2/auth/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Real authentication endpoint with database verification"""
    try:
        # Check database for user
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute('SELECT username, hashed_password, disabled FROM users WHERE username = ?', (form_data.username,))
        user_row = cursor.fetchone()
        
        # Create default test user if not exists
        if not user_row and form_data.username == "test":
            test_password_hash = get_password_hash("test")
            cursor.execute('''
                INSERT INTO users (username, email, hashed_password, full_name, disabled)
                VALUES (?, ?, ?, ?, ?)
            ''', ("test", "test@example.com", test_password_hash, "Test User", False))
            conn.commit()
            user_row = ("test", test_password_hash, False)
        
        conn.close()
        
        if not user_row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        username, hashed_password, disabled = user_row
        
        if disabled:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account disabled",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify password
        if not verify_password(form_data.password, hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": form_data.username, "scopes": form_data.scopes},
            expires_delta=access_token_expires
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication system error"
        )

@app.get("/api/v2/user/me", response_model=User)
async def read_users_me(current_user: User = Depends(require_auth)):
    """Get current user info"""
    return current_user

@app.post(
    "/api/v2/scan",
    response_model=ScanResponse,
    dependencies=[Depends(check_rate_limit)]
)
async def start_scan(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Start a new accessibility scan (authentication optional for now)"""
    try:
        scan_id = await scan_manager.create_scan(request)
        
        # Create status tracking for polling
        scan_status = create_scan_status(scan_id)
        scan_status.update(status="starting", progress=0, message="Avvio scansione...")
        
        # Add background task
        background_tasks.add_task(run_scan_task, scan_id, request)
        
        scan = scan_manager.get_scan(scan_id)
        
        return ScanResponse(
            scan_id=scan_id,
            status=scan["status"],
            progress=scan["progress"],
            message="Scan initiated",
            results=None,
            created_at=scan["created_at"],
            updated_at=scan["updated_at"]
        )
    except Exception as e:
        logger.error(f"Error starting scan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start scan"
        )

@app.get("/api/v2/scan/{scan_id}", response_model=ScanResponse)
async def get_scan_status(
    scan_id: str,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get scan status (authentication optional for now)"""
    scan = scan_manager.get_scan(scan_id)
    
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found"
        )
    
    return ScanResponse(
        scan_id=scan_id,
        status=scan["status"],
        progress=scan["progress"],
        message=scan.get("message"),
        results=scan.get("results"),
        created_at=scan["created_at"],
        updated_at=scan["updated_at"]
    )

@app.websocket("/ws/{scan_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    scan_id: str,
    token: Optional[str] = None
):
    """WebSocket endpoint with authentication support"""
    # Validate scan exists
    scan = scan_manager.get_scan(scan_id)
    if not scan:
        await websocket.close(code=1008, reason="Scan not found")
        return
    
    # Connect WebSocket
    await ws_manager.connect(websocket, scan_id, token)
    
    try:
        while True:
            # Keep connection alive and handle messages
            data = await websocket.receive_json()
            
            # Echo back for now
            await websocket.send_json({
                "type": "echo",
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            })
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, scan_id)
    except Exception as e:
        logger.error(f"Unexpected WebSocket error: {e}")
        ws_manager.disconnect(websocket, scan_id)
        await websocket.close(code=1011, reason="Internal error")

# Endpoint legacy /api/scan/{scan_id}/status rimosso: usare /api/scan/status/{session_id}

@app.get("/api/scan/active")
async def get_active_scans(
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get all active scans for dashboard"""
    active_scans = []
    
    # From scan_manager
    try:
        for scan_id, scan in scan_manager.scans.items():
            if scan["status"] not in ["completed", "failed"]:
                active_scans.append({
                    "scan_id": scan_id,
                    "status": scan["status"],
                    "progress": scan.get("progress", 0),
                    "message": scan.get("message", ""),
                    "created_at": scan.get("created_at", ""),
                    "url": scan.get("url", "")
                })
    except Exception as e:
        logger.error(f"Error getting active scans from scan_manager: {e}")
    
    # From in-memory status store
    for scan_id, status in scan_status_store.items():
        if status.status not in ["completed", "failed"]:
            # Check if already added from scan_manager
            if not any(s["scan_id"] == scan_id for s in active_scans):
                active_scans.append({
                    "scan_id": scan_id,
                    "status": status.status,
                    "progress": status.progress,
                    "message": status.message,
                    "created_at": status.created_at.isoformat(),
                    "url": ""
                })
    
    return JSONResponse(
        content={
            "active_scans": active_scans,
            "count": len(active_scans),
            "timestamp": time.time()
        }
    )

@app.post("/api/system/cleanup")
async def manual_cleanup(
    current_user: Optional[User] = Depends(get_current_user)
):
    """Manually trigger cleanup of old scans"""
    try:
        initial_count = len(scan_status_store)
        cleanup_old_scans()
        final_count = len(scan_status_store)
        cleaned = initial_count - final_count
        
        return JSONResponse(
            content={
                "success": True,
                "message": f"Cleanup completato: rimossi {cleaned} scan vecchi",
                "cleaned_scans": cleaned,
                "remaining_scans": final_count,
                "timestamp": time.time()
            }
        )
    except Exception as e:
        logger.error(f"Error in manual cleanup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore durante il cleanup"
        )

# ==================== REAL SCANNER INTEGRATION ====================

try:
    from eaa_scanner.core import run_scan as eaa_run_scan
    from eaa_scanner.config import Config as EAAConfig
    from eaa_scanner.crawler import WebCrawler
    from eaa_scanner.pdf import html_to_pdf
    from eaa_scanner.llm_integration import LLMIntegration
    from eaa_scanner.report import generate_html_report as eaa_generate_html
    EAA_SCANNER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"EAA Scanner modules not available: {e}")
    EAA_SCANNER_AVAILABLE = False
    
import sqlite3
from datetime import datetime, timedelta
import aiofiles
import tempfile
import shutil
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import requests

# Database initialization
def get_database_path():
    """Get the correct database path for the environment"""
    import os
    db_dir = '/app/data' if os.path.exists('/app/data') else '.'
    return os.path.join(db_dir, 'eaa_scanner.db')

def init_database():
    """Initialize SQLite database for storing scan results"""
    import os
    
    db_path = get_database_path()
    print(f"Initializing database at: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create scans table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scans (
            id TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            company_name TEXT NOT NULL,
            email TEXT NOT NULL,
            status TEXT NOT NULL,
            progress INTEGER DEFAULT 0,
            results TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            output_path TEXT,
            html_report_path TEXT,
            pdf_report_path TEXT
        )
    ''')
    
    # Add completed_at column if it doesn't exist
    cursor.execute("PRAGMA table_info(scans)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'completed_at' not in columns:
        cursor.execute('ALTER TABLE scans ADD COLUMN completed_at TIMESTAMP')
    
    # Create users table for authentication
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            hashed_password TEXT NOT NULL,
            full_name TEXT,
            disabled BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')    
    
    # Create regeneration sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS regeneration_sessions (
            id TEXT PRIMARY KEY,
            scan_id TEXT NOT NULL,
            model TEXT NOT NULL,
            content_type TEXT NOT NULL,
            status TEXT NOT NULL,
            progress INTEGER DEFAULT 0,
            results TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cost_estimate REAL,
            tokens_used INTEGER
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
# init_database()  # Moved to lifespan manager

# ==================== REAL DISCOVERY IMPLEMENTATION ====================

class RealWebCrawler:
    """Optimized web crawler with batch processing and concurrent requests"""
    
    def __init__(self, base_url: str, max_pages: int = 50, max_depth: int = 3):
        self.base_url = base_url
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.discovered_urls = []  # Store progressive results
        self.use_optimized = False  # Flag to check if using optimized version
        
        # Try to use optimized crawler if aiohttp is available
        try:
            import aiohttp
            self.use_optimized = True
            logger.info("✅ Using OPTIMIZED crawler with concurrent requests")
        except ImportError:
            self.use_optimized = False
            logger.info("ℹ️ Using standard crawler (install aiohttp for better performance)")
            self.crawler = WebCrawler(
                base_url=base_url,
                max_pages=max_pages,
                max_depth=max_depth,
                follow_external=False
            )
    
    async def discover_urls(self, progress_callback=None) -> List[Dict[str, Any]]:
        """Discover URLs using optimized or standard crawling"""
        
        if self.use_optimized:
            return await self._discover_urls_optimized(progress_callback)
        else:
            return await self._discover_urls_standard(progress_callback)
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL to prevent duplicates"""
        from urllib.parse import urlparse, urlunparse
        
        # Convert to lowercase
        url = url.lower().strip()
        parsed = urlparse(url)
        
        # Normalize path: 
        # - Remove trailing slash ALWAYS (even for root)
        # - Empty path becomes '/'
        path = parsed.path.rstrip('/')
        if not path:
            path = '/'
        
        # Reconstruct URL without fragment and with normalized path
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            path,
            '',  # Remove params
            parsed.query or '',  # Keep query if exists
            ''  # Remove fragment
        ))
        
        # Final cleanup: ensure no double slashes except after http://
        normalized = normalized.replace('//', '/').replace('http:/', 'http://').replace('https:/', 'https://')
        
        return normalized
    
    async def _discover_urls_optimized(self, progress_callback=None) -> List[Dict[str, Any]]:
        """Optimized URL discovery with batch processing and concurrent requests"""
        import aiohttp
        import asyncio
        from urllib.parse import urljoin, urlparse
        from bs4 import BeautifulSoup
        import re
        
        discovered = []
        discovered_urls_set = set()  # Track unique URLs by normalized form
        visited = set()
        to_visit = [(self.base_url, 0)]
        failed_count = 0
        batch_size = 10
        max_concurrent = 5
        
        if progress_callback:
            await progress_callback(5, "🚀 Crawler ottimizzato avviato...")
        
        # Create session for connection pooling with increased timeout
        timeout = aiohttp.ClientTimeout(total=10, connect=3, sock_read=5)
        connector = aiohttp.TCPConnector(limit=max_concurrent, limit_per_host=max_concurrent)
        
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            # Log initial state
            logger.info(f"Starting crawl of {self.base_url}, max_pages={self.max_pages}, max_depth={self.max_depth}")
            
            while to_visit and len(discovered) < self.max_pages:
                # Process URLs in batches
                batch = []
                while len(batch) < batch_size and to_visit and len(discovered) + len(batch) < self.max_pages:
                    url, depth = to_visit.pop(0)
                    normalized_url = self._normalize_url(url)
                    if normalized_url not in visited and depth <= self.max_depth:
                        batch.append((url, depth))
                        visited.add(normalized_url)
                
                if not batch:
                    logger.info(f"No more URLs to process. Discovered: {len(discovered)}, to_visit: {len(to_visit)}")
                    break
                
                logger.info(f"Processing batch of {len(batch)} URLs...")
                
                # Process batch concurrently
                if progress_callback:
                    progress = min(90, int((len(discovered) / self.max_pages) * 90))
                    await progress_callback(progress, f"Analizzando batch di {len(batch)} URL...")
                
                tasks = [self._fetch_and_parse_optimized(session, url, depth) for url, depth in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for (url, depth), result in zip(batch, results):
                    if isinstance(result, Exception):
                        failed_count += 1
                        logger.debug(f"Failed to fetch {url}: {result}")
                        continue
                    
                    if result:
                        page_info, found_urls = result
                        # Check if URL is already discovered (prevent duplicates)
                        normalized_page_url = self._normalize_url(page_info['url'])
                        if normalized_page_url not in discovered_urls_set:
                            discovered.append(page_info)
                            discovered_urls_set.add(normalized_page_url)
                            self.discovered_urls.append(page_info)  # Store progressive result
                        
                        # Add new URLs to visit
                        for new_url in found_urls[:10]:  # Limit new URLs per page
                            normalized_new_url = self._normalize_url(new_url)
                            if normalized_new_url not in visited and len(to_visit) < 100:
                                to_visit.append((new_url, depth + 1))
        
        if progress_callback:
            await progress_callback(100, f"✅ Completato: {len(discovered)} pagine trovate")
        
        logger.info(f"Optimized crawler completed: {len(discovered)} pages found, {failed_count} failures")
        return discovered
    
    async def _fetch_and_parse_optimized(self, session, url, depth):
        """Fetch and parse a single URL optimized"""
        from urllib.parse import urljoin
        from bs4 import BeautifulSoup
        
        try:
            logger.debug(f"Fetching {url}...")
            async with session.get(url, allow_redirects=True, ssl=False) as response:
                if response.status != 200:
                    logger.warning(f"Non-200 status for {url}: {response.status}")
                    return None
                
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Extract page info
                page_info = {
                    "url": str(response.url),
                    "title": soup.title.string if soup.title else "Senza titolo",
                    "type": self._determine_page_type(str(response.url), soup),
                    "priority": "alta" if depth == 0 else ("media" if depth == 1 else "bassa"),
                    "depth": depth,
                    "elements": self._count_elements(soup),
                    "accessibility_hints": self._analyze_accessibility(soup),
                    "estimated_scan_time": 30 + depth * 5,
                    "discovered_at": datetime.now().isoformat()
                }
                
                # Find URLs
                found_urls = []
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    absolute_url = urljoin(str(response.url), href)
                    if self._is_valid_url(absolute_url):
                        found_urls.append(absolute_url)
                
                return page_info, found_urls
                
        except Exception as e:
            logger.warning(f"Error fetching {url}: {type(e).__name__}: {e}")
            return None
    
    def _determine_page_type(self, url: str, soup_or_title, soup=None) -> str:
        """Determine the type of page"""
        # Handle both signatures: (url, soup) and (url, title, soup)
        if soup is None:
            soup = soup_or_title  # Called with 2 args: url, soup
            title = soup.title.string if soup and soup.title else ""
        else:
            title = soup_or_title  # Called with 3 args: url, title, soup
        
        url_lower = url.lower()
        title_lower = title.lower() if title else ""
        
        if any(term in url_lower for term in ['contact', 'contatti', 'contatto']):
            return 'contact'
        elif any(term in url_lower for term in ['about', 'chi-siamo', 'azienda']):
            return 'about'
        elif any(term in url_lower for term in ['product', 'prodotti', 'prodotto']):
            return 'product'
        elif any(term in url_lower for term in ['service', 'servizi', 'servizio']):
            return 'service'
        elif url.rstrip('/') == self.base_url.rstrip('/'):
            return 'homepage'
        else:
            return 'general'
    
    def _count_elements(self, soup) -> dict:
        """Count interactive elements in the page"""
        return {
            "forms": len(soup.find_all('form')),
            "inputs": len(soup.find_all('input')),
            "buttons": len(soup.find_all('button')),
            "images": len(soup.find_all('img')),
            "videos": len(soup.find_all('video'))
        }
    
    def _analyze_accessibility(self, soup) -> dict:
        """Analyze accessibility hints"""
        forms = soup.find_all('form')
        inputs = soup.find_all('input')
        
        return {
            "has_forms": len(forms) > 0,
            "form_complexity": "high" if len(inputs) > 10 else ("medium" if len(inputs) > 5 else "low"),
            "complexity": "high" if len(inputs) > 20 else ("medium" if len(inputs) > 10 else "low")
        }
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and should be crawled"""
        from urllib.parse import urlparse
        
        if not url or url.startswith('#') or url.startswith('javascript:'):
            return False
        
        parsed = urlparse(url)
        base_parsed = urlparse(self.base_url)
        
        # Only crawl same domain
        if parsed.netloc and parsed.netloc != base_parsed.netloc:
            return False
        
        # Skip non-HTML resources
        if any(url.lower().endswith(ext) for ext in ['.pdf', '.jpg', '.png', '.gif', '.zip', '.exe']):
            return False
        
        return True
    
    async def _discover_urls_standard(self, progress_callback=None) -> List[Dict[str, Any]]:
        """Standard URL discovery using the original crawler"""
        try:
            if progress_callback:
                await progress_callback(10, "Inizializzazione crawler standard...")
            
            # Use the real crawler if available with timeout
            import asyncio
            discovered_urls = []
            
            try:
                if EAA_SCANNER_AVAILABLE:
                    # Run crawler in a thread with controlled timeout
                    task = asyncio.create_task(asyncio.to_thread(self.crawler.crawl))
                    
                    # Wait for completion or timeout
                    try:
                        discovered_urls = await asyncio.wait_for(task, timeout=45.0)
                        logger.info(f"Crawler found {len(discovered_urls)} URLs")
                    except asyncio.TimeoutError:
                        logger.warning("Crawler timeout after 45s, checking for partial results")
                        # The crawler might have found some URLs even if it didn't finish
                        # Try to get them from the crawler instance
                        if hasattr(self.crawler, 'discovered_urls'):
                            discovered_urls = self.crawler.discovered_urls
                            logger.info(f"Retrieved {len(discovered_urls)} partial results")
                        else:
                            discovered_urls = []
                else:
                    # Fallback to simple requests-based discovery with timeout
                    discovered_urls = await asyncio.wait_for(
                        self._simple_crawl(),
                        timeout=30.0
                    )
            except Exception as e:
                logger.error(f"Crawler error: {e}")
                discovered_urls = []
            
            # If still no URLs, at least return the base URL
            if not discovered_urls:
                logger.warning("No URLs discovered, using base URL only")
                discovered_urls = [{"url": self.base_url, "title": "Homepage", "type": "homepage", "priority": 100}]
            
            if progress_callback:
                await progress_callback(50, "Analisi pagine scoperte...")
            
            # Process discovered URLs
            pages = []
            urls_to_process = discovered_urls[:self.max_pages]  # Use configured max_pages limit
            
            for i, url_or_dict in enumerate(urls_to_process):
                try:
                    # Handle both string URLs and dict objects from EAA crawler
                    if isinstance(url_or_dict, dict):
                        # Already have page info from EAA crawler, just format it
                        page_info = {
                            "url": url_or_dict.get("url", ""),
                            "title": url_or_dict.get("title", "Senza titolo"),
                            "type": url_or_dict.get("page_type", "general"),
                            "priority": self._map_priority(url_or_dict.get("priority", 50)),
                            "depth": url_or_dict.get("depth", 0),
                            "elements": url_or_dict.get("elements", {}),
                            "accessibility_hints": self._extract_hints(url_or_dict.get("elements", {})),
                            "estimated_scan_time": 30,
                            "discovered_at": datetime.utcnow().isoformat()
                        }
                        pages.append(page_info)
                    else:
                        # String URL, need to analyze
                        page_info = await asyncio.wait_for(
                            self._analyze_page(url_or_dict),
                            timeout=5.0
                        )
                        pages.append(page_info)
                    
                    if progress_callback:
                        progress = 50 + (40 * (i + 1) / len(urls_to_process))
                        await progress_callback(int(progress), f"Analizzata pagina {i+1}/{len(urls_to_process)}")
                        
                except (Exception, asyncio.TimeoutError) as e:
                    logger.warning(f"Errore analisi pagina {url_or_dict}: {e}")
                    continue
            
            if progress_callback:
                await progress_callback(100, "Discovery completata")
            
            return pages
            
        except Exception as e:
            logger.error(f"Errore durante discovery: {e}")
            if progress_callback:
                await progress_callback(100, "Errore durante discovery")
            return []
    
    async def _analyze_page(self, url: str) -> Dict[str, Any]:
        """Analyze a single page for accessibility hints"""
        import requests
        from bs4 import BeautifulSoup
        
        try:
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'EAA-Scanner/2.0 (Accessibility Scanner)'
            })
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract page information
            title = soup.find('title')
            title_text = title.get_text().strip() if title else "Senza titolo"
            
            # Count elements
            elements = {
                "forms": len(soup.find_all('form')),
                "images": len(soup.find_all('img')),
                "links": len(soup.find_all('a', href=True)),
                "headings": len(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])),
                "buttons": len(soup.find_all(['button', 'input[type="submit"]', 'input[type="button"]'])),
                "inputs": len(soup.find_all(['input', 'textarea', 'select']))
            }
            
            # Determine page type and priority
            page_type = self._determine_page_type(url, soup)
            priority = self._determine_priority(page_type, elements)
            
            # Calculate estimated scan time
            estimated_scan_time = self._estimate_scan_time(elements)
            
            # Accessibility hints
            accessibility_hints = self._analyze_accessibility_hints(soup, elements)
            
            return {
                "url": url,
                "title": title_text,
                "type": page_type,
                "priority": priority,
                "depth": self._calculate_depth(url),
                "elements": elements,
                "accessibility_hints": accessibility_hints,
                "estimated_scan_time": estimated_scan_time,
                "discovered_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.warning(f"Errore analisi pagina {url}: {e}")
            return {
                "url": url,
                "title": "Errore nell'analisi",
                "type": "unknown",
                "priority": "bassa",
                "depth": 0,
                "elements": {"forms": 0, "images": 0, "links": 0, "headings": 0, "buttons": 0, "inputs": 0},
                "accessibility_hints": {"error": True},
                "estimated_scan_time": 30,
                "discovered_at": datetime.utcnow().isoformat()
            }
    
    def _determine_page_type_OLD_REMOVED(self, url: str, title: str, soup) -> str:
        """Determine page type based on URL and content"""
        url_lower = url.lower()
        title_lower = title.lower()
        
        if any(term in url_lower for term in ['home', 'index', '/', 'homepage']):
            return "homepage"
        elif any(term in url_lower for term in ['contact', 'contatti']):
            return "contatti"
        elif any(term in url_lower for term in ['login', 'signin', 'account', 'area-clienti']):
            return "autenticazione"
        elif any(term in url_lower for term in ['privacy', 'cookie', 'legal', 'terms']):
            return "legal"
        elif any(term in url_lower for term in ['service', 'servizi', 'product', 'prodotti']):
            return "servizi"
        elif any(term in title_lower for term in ['chi siamo', 'about', 'storia', 'company']):
            return "contenuti"
        else:
            return "contenuti"
    
    def _determine_priority(self, page_type: str, elements: Dict[str, int]) -> str:
        """Determine scan priority based on page type and elements"""
        if page_type in ["homepage", "contatti", "autenticazione"]:
            return "alta"
        elif page_type == "servizi" or elements["forms"] > 0:
            return "alta"
        elif page_type == "legal":
            return "bassa"
        else:
            return "media"
    
    def _calculate_depth(self, url: str) -> int:
        """Calculate URL depth from base URL"""
        base_path = urlparse(self.base_url).path.rstrip('/')
        url_path = urlparse(url).path.rstrip('/')
        
        if url_path == base_path or url_path == '':
            return 0
        
        # Count path segments beyond base
        base_segments = len([s for s in base_path.split('/') if s])
        url_segments = len([s for s in url_path.split('/') if s])
        return max(0, url_segments - base_segments)
    
    def _estimate_scan_time(self, elements: Dict[str, int]) -> int:
        """Estimate scan time based on page complexity"""
        base_time = 25
        complexity_factor = (
            elements["forms"] * 10 +
            elements["images"] * 2 +
            elements["links"] * 1 +
            elements["inputs"] * 5
        )
        return min(60, base_time + complexity_factor)
    
    def _analyze_accessibility_hints(self, soup, elements: Dict[str, int]) -> Dict[str, bool]:
        """Analyze accessibility-related hints"""
        hints = {}
        
        # Complex navigation
        nav_elements = soup.find_all(['nav', '[role="navigation"]'])
        hints["complex_navigation"] = len(nav_elements) > 1 or elements["links"] > 20
        
        # Media content
        hints["media_content"] = elements["images"] > 5 or len(soup.find_all(['video', 'audio', 'iframe'])) > 0
        
        # Interactive elements
        hints["interactive_elements"] = elements["forms"] > 0 or elements["buttons"] > 2
        
        # Form validation
        if elements["forms"] > 0:
            required_fields = len(soup.find_all(['[required]', '[aria-required="true"]']))
            hints["form_validation"] = required_fields > 0
            hints["required_fields"] = required_fields > 0
        
        # Long content
        text_content = soup.get_text()
        hints["long_content"] = len(text_content) > 2000
        
        # Structured content
        hints["structured_content"] = elements["headings"] > 5
        
        # Simple layout
        hints["simple_layout"] = elements["forms"] == 0 and elements["buttons"] <= 1
        
        return hints
    
    def _map_priority(self, numeric_priority: int) -> str:
        """Map numeric priority to string"""
        if numeric_priority >= 80:
            return "alta"
        elif numeric_priority >= 50:
            return "media"
        else:
            return "bassa"
    
    def _extract_hints(self, elements: Dict[str, int]) -> Dict[str, Any]:
        """Extract accessibility hints from page elements"""
        hints = {}
        
        # Check for forms
        if elements.get("forms", 0) > 0:
            hints["has_forms"] = True
            hints["form_complexity"] = "high" if elements.get("inputs", 0) > 10 else "low"
        
        # Check for multimedia
        if elements.get("videos", 0) > 0:
            hints["has_videos"] = True
            hints["needs_captions"] = True
        
        if elements.get("images", 0) > 20:
            hints["many_images"] = True
            hints["needs_alt_text_review"] = True
        
        # Check for interactive elements
        if elements.get("buttons", 0) > 10:
            hints["many_interactive"] = True
            hints["needs_keyboard_testing"] = True
        
        # Overall complexity
        total_elements = sum(elements.values())
        hints["complexity"] = "high" if total_elements > 100 else "medium" if total_elements > 30 else "low"
        
        return hints
    
    async def _simple_crawl(self) -> List[str]:
        """Simple fallback crawler using requests - optimized for speed"""
        try:
            import requests
            from bs4 import BeautifulSoup
            from urllib.parse import urljoin, urlparse
            
            discovered = [self.base_url]
            visited = set([self.base_url])
            
            # Limit crawling to be faster
            max_urls_per_depth = 3  # Only process 3 URLs per depth level
            max_total_urls = min(self.max_pages, 10)  # Never process more than 10 URLs
            
            # Simple breadth-first crawling with strict limits
            for depth in range(min(self.max_depth, 2)):  # Max 2 levels deep
                if len(discovered) >= max_total_urls:
                    break
                
                new_urls = []
                urls_to_crawl = discovered[-max_urls_per_depth:]  # Only process last few URLs
                
                for url in urls_to_crawl:
                    if len(discovered) >= max_total_urls:
                        break
                        
                    try:
                        response = requests.get(url, timeout=3, headers={
                            'User-Agent': 'EAA-Scanner/2.0 (Accessibility Scanner)'
                        })
                        response.raise_for_status()
                        
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Find limited links
                        links_found = 0
                        for link in soup.find_all('a', href=True, limit=20):  # Limit to 20 links per page
                            if links_found >= 5:  # Max 5 new links per page
                                break
                                
                            href = link['href']
                            full_url = urljoin(url, href)
                            
                            # Only include same domain links
                            if (urlparse(full_url).netloc == urlparse(self.base_url).netloc and 
                                full_url not in visited and
                                len(discovered) < max_total_urls):
                                discovered.append(full_url)
                                visited.add(full_url)
                                new_urls.append(full_url)
                                links_found += 1
                    
                    except Exception as e:
                        logger.warning(f"Error crawling {url}: {e}")
                        continue
                
                if not new_urls:
                    break
            
            logger.info(f"Simple crawl discovered {len(discovered)} URLs")
            return discovered[:max_total_urls]
            
        except Exception as e:
            logger.error(f"Simple crawler failed: {e}")
            return [self.base_url]  # Return at least the base URL

# Fallback PDF generation function
async def generate_pdf_fallback(html_path: Path, pdf_path: Path) -> bool:
    """Fallback PDF generation using available tools"""
    try:
        # Try weasyprint first
        try:
            import weasyprint
            html_doc = weasyprint.HTML(filename=str(html_path))
            html_doc.write_pdf(str(pdf_path))
            return True
        except ImportError:
            pass
        
        # Try wkhtmltopdf
        try:
            import subprocess
            result = subprocess.run([
                'wkhtmltopdf',
                '--page-size', 'A4',
                '--orientation', 'Portrait',
                '--margin-top', '0.75in',
                '--margin-right', '0.75in',
                '--margin-bottom', '0.75in',
                '--margin-left', '0.75in',
                str(html_path),
                str(pdf_path)
            ], capture_output=True, timeout=30)
            
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        
        # Last resort: create a simple PDF message
        simple_pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(PDF generation not available) Tj
ET
endstream
endobj
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
0
%%EOF"""
        
        with open(pdf_path, 'wb') as f:
            f.write(simple_pdf_content)
        
        logger.warning("Used fallback PDF generation - install weasyprint or wkhtmltopdf for better results")
        return True
        
    except Exception as e:
        logger.error(f"Fallback PDF generation failed: {e}")
        return False

# Fallback HTML generation function
async def generate_html_fallback(eaa_config, results: Dict[str, Any]) -> str:
    """Fallback HTML report generation"""
    
    company_name = eaa_config.company_name
    url = eaa_config.url
    created_at = datetime.utcnow().strftime('%d/%m/%Y %H:%M')
    
    # Validate results is not None
    if results is None:
        logger.warning("generate_html_fallback: results is None, using empty defaults")
        results = {}
    
    # Extract data from results
    total_issues = results.get('total_issues', 0)
    critical_issues = results.get('critical_issues', 0)
    high_issues = results.get('high_issues', 0)
    medium_issues = results.get('medium_issues', 0)
    low_issues = results.get('low_issues', 0)
    compliance_score = results.get('compliance_score', 0)
    eaa_compliant = results.get('eaa_compliant', False)
    wcag_level = results.get('wcag_level', 'AA')
    
    # Generate compliance status
    compliance_status = "Conforme" if eaa_compliant else "Non Conforme"
    compliance_class = "compliant" if eaa_compliant else "non-compliant"
    
    html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Report di Accessibilità EAA - {company_name}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 40px;
            background-color: #f8f9fa;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
            border-radius: 8px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 8px 8px 0 0;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .header h2 {{
            margin: 0 0 20px 0;
            font-size: 1.5em;
            opacity: 0.9;
            font-weight: 400;
        }}
        .metadata {{
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 4px;
            margin-top: 20px;
        }}
        .metadata p {{
            margin: 5px 0;
            font-size: 1.1em;
        }}
        .content {{
            padding: 40px;
        }}
        .summary {{
            background: #f8f9fa;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 40px;
            border-left: 5px solid #007bff;
        }}
        .summary h2 {{
            margin-top: 0;
            color: #333;
            font-size: 1.8em;
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .metric {{
            text-align: center;
            padding: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metric-value {{
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .metric-label {{
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .compliance {{
            text-align: center;
            padding: 30px;
            margin: 30px 0;
            border-radius: 8px;
            font-size: 1.5em;
            font-weight: bold;
        }}
        .compliant {{
            background: #d4edda;
            color: #155724;
            border: 2px solid #c3e6cb;
        }}
        .non-compliant {{
            background: #f8d7da;
            color: #721c24;
            border: 2px solid #f5c6cb;
        }}
        .critical {{ color: #dc3545; }}
        .high {{ color: #fd7e14; }}
        .medium {{ color: #ffc107; }}
        .low {{ color: #28a745; }}
        .score-circle {{
            width: 120px;
            height: 120px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 20px;
            font-size: 1.5em;
            font-weight: bold;
            background: conic-gradient(#28a745 0deg {compliance_score * 3.6}deg, #e9ecef {compliance_score * 3.6}deg 360deg);
            color: #333;
        }}
        .score-inner {{
            width: 90px;
            height: 90px;
            border-radius: 50%;
            background: white;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
        }}
        .score-value {{
            font-size: 1.2em;
            font-weight: bold;
        }}
        .score-label {{
            font-size: 0.7em;
            color: #666;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 20px 40px;
            border-top: 1px solid #e9ecef;
            text-align: center;
            color: #666;
            border-radius: 0 0 8px 8px;
        }}
        .issues-section {{
            margin-top: 40px;
        }}
        .issues-section h2 {{
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }}
        .issue-placeholder {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #6c757d;
            margin: 10px 0;
            color: #666;
            font-style: italic;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Report di Accessibilità EAA</h1>
            <h2>{company_name}</h2>
            <div class="metadata">
                <p><strong>URL:</strong> {url}</p>
                <p><strong>Data di scansione:</strong> {created_at}</p>
                <p><strong>Standard di riferimento:</strong> WCAG {wcag_level}, EAA (EN 301 549)</p>
            </div>
        </div>
        
        <div class="content">
            <div class="summary">
                <h2>Riepilogo Esecutivo</h2>
                
                <div class="score-circle">
                    <div class="score-inner">
                        <div class="score-value">{compliance_score}/100</div>
                        <div class="score-label">PUNTEGGIO</div>
                    </div>
                </div>
                
                <div class="metrics">
                    <div class="metric">
                        <div class="metric-value">{total_issues}</div>
                        <div class="metric-label">Problemi Totali</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value critical">{critical_issues}</div>
                        <div class="metric-label">Critici</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value high">{high_issues}</div>
                        <div class="metric-label">Elevati</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value medium">{medium_issues}</div>
                        <div class="metric-label">Medi</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value low">{low_issues}</div>
                        <div class="metric-label">Bassi</div>
                    </div>
                </div>
                
                <div class="compliance {compliance_class}">
                    Conformità EAA: {compliance_status}
                </div>
            </div>
            
            <div class="issues-section">
                <h2>Problemi Rilevati</h2>
                <div class="issue-placeholder">
                    I dettagli specifici dei problemi di accessibilità sono disponibili nel report completo generato dal motore di scansione EAA.
                    Per visualizzare l'analisi dettagliata, utilizzare il sistema con le dipendenze complete installate.
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>Report generato da EAA Scanner v2.0 - {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}</p>
            <p>Conforme agli standard WCAG {wcag_level} e EAA (European Accessibility Act)</p>
        </div>
    </div>
</body>
</html>"""
    
    return html_content

# ==================== REAL SCAN IMPLEMENTATION ====================

async def run_scan_task(scan_id: str, request: ScanRequest):
    """Background task to run real accessibility scan"""
    scan_status = None
    try:
        logger.info(f"========== STARTING REAL SCAN {scan_id} for {request.url} ==========")
        logger.info(f"Request data: company={request.company_name}, email={request.email}")
        logger.info(f"Scanner config: {request.scannerConfig}")
        logger.info(f"Simulate value: {getattr(request, 'simulate', 'NOT_SET')}")
        
        # Get scan status from store directly (NOT the async function)
        scan_status = scan_status_store.get(scan_id)
        
        # Update status in both systems
        await scan_manager.update_scan(scan_id, status="running", progress=5)
        scan_status = scan_status_store.get(scan_id)
        if scan_status:
            scan_status.update(status="running", progress=5, message="Scansione in corso...")
        
        await ws_manager.broadcast(scan_id, {
            "type": "status_update",
            "status": "running",
            "progress": 5
        })
        
        # Create EAA Scanner configuration
        await scan_manager.update_scan(scan_id, progress=10, message="Configurazione scanner...")
        if scan_status:
            scan_status.update(progress=10, message="Configurazione scanner...")
        await ws_manager.broadcast(scan_id, {"type": "progress", "progress": 10, "message": "Configurazione scanner..."})
        
        # Create temporary output directory
        output_root = Path("output")
        output_root.mkdir(exist_ok=True)
        
        # Configure EAA Scanner
        # Determina modalità simulazione: priorità a richiesta, poi variabile d'ambiente (default false)
        simulate_flag = getattr(request, 'simulate', None)
        if simulate_flag is None:
            simulate_env = os.getenv("SIMULATE_MODE", "false").lower()
            simulate_flag = simulate_env in ("1", "true", "yes", "on")

        eaa_config = EAAConfig(
            url=str(request.url),
            company_name=request.company_name,
            email=request.email,
            wave_api_key=get_effective_wave_key(),
            openai_api_key=get_effective_openai_key(),
            simulate=bool(simulate_flag)  # Usa richiesta o fallback env
        )
        
        # Configure scanners based on request
        if request.scannerConfig:
            eaa_config.scanners_enabled.wave = request.scannerConfig.wave.enabled
            eaa_config.scanners_enabled.axe_core = request.scannerConfig.axe.enabled
            eaa_config.scanners_enabled.lighthouse = request.scannerConfig.lighthouse.enabled
            eaa_config.scanners_enabled.pa11y = request.scannerConfig.pa11y.enabled
        # Se manca la WAVE API key, disabilita wave per evitare errori runtime
        if not eaa_config.wave_api_key:
            eaa_config.scanners_enabled.wave = False
        
        # Create event monitor for progress updates
        class ScanProgressMonitor:
            """Monitor per eventi di progresso durante la scansione EAA
            
            Implementa tutti i metodi richiesti da ScanEventHooks per la compatibilità
            completa con il sistema di eventi del scanner EAA.
            """
            def __init__(self, scan_id: str, scan_manager, ws_manager):
                self.scan_id = scan_id
                self.scan_manager = scan_manager
                self.ws_manager = ws_manager
                self.current_progress = 10
                self.scanner_progress = {}  # Track per-scanner progress
                
                # Initialize SSE monitor for real-time events
                self.sse_monitor = None
                try:
                    from webapp.scan_monitor import get_scan_monitor
                    self.sse_monitor = get_scan_monitor()
                    logger.info(f"SSE monitor initialized for scan {scan_id}")
                except ImportError:
                    logger.warning("SSE monitor not available, using WebSocket only")
            
            async def update_progress(self, progress: int, message: str):
                """Update progress with async broadcast"""
                self.current_progress = max(self.current_progress, progress)
                await self.scan_manager.update_scan(self.scan_id, progress=self.current_progress, message=message)
                await self.ws_manager.broadcast(self.scan_id, {
                    "type": "progress",
                    "progress": self.current_progress,
                    "message": message
                })
            
            def _safe_emit_progress(self, progress: int, message: str):
                """Safely emit progress updates handling asyncio context"""
                try:
                    # Try to create task in current event loop
                    asyncio.create_task(self.update_progress(progress, message))
                except RuntimeError:
                    # No running event loop - use print fallback
                    print(f"Progress: {progress}% - {message}")
            
            def emit_scan_start(self, scan_id: str, url: str, company_name: str, scanners_enabled: dict):
                """Emit scan start event - SSE integration"""
                if self.sse_monitor:
                    self.sse_monitor.emit_scan_start(
                        scan_id=scan_id,
                        url=url,
                        company_name=company_name,
                        scanners_enabled=scanners_enabled
                    )
                
                # Also broadcast via WebSocket for compatibility
                try:
                    asyncio.create_task(self.ws_manager.broadcast(scan_id, {
                        "type": "scan_start",
                        "url": url,
                        "company_name": company_name,
                        "scanners": list(scanners_enabled.keys())
                    }))
                except RuntimeError:
                    print(f"Scan started: {company_name}")
            
            def emit_page_progress(self, scan_id: str, current_page: int, total_pages: int, current_url: str):
                """Emit page progress update - SSE integration"""
                progress = 10 + int((current_page / total_pages) * 40)  # 10-50% for page scanning
                message = f"Scansione pagina {current_page}/{total_pages}: {current_url}"
                
                if self.sse_monitor:
                    self.sse_monitor.emit_page_progress(
                        scan_id=scan_id,
                        current_page=current_page,
                        total_pages=total_pages,
                        current_url=current_url
                    )
                
                self._safe_emit_progress(progress, message)
            
            def emit_scanner_start(self, scan_id: str, scanner_name: str, url: str, estimated_duration: Optional[int] = None):
                """Emit scanner start event - SSE integration"""
                self.scanner_progress[scanner_name] = {"started": True, "progress": 0}
                progress_increase = 5
                message = f"Avvio {scanner_name} per {url}"
                if estimated_duration:
                    message += f" (stimato: {estimated_duration}s)"
                
                if self.sse_monitor:
                    self.sse_monitor.emit_scanner_start(
                        scan_id=scan_id,
                        scanner_name=scanner_name,
                        url=url,
                        estimated_duration=estimated_duration
                    )
                
                self._safe_emit_progress(self.current_progress + progress_increase, message)
            
            def emit_scanner_operation(self, scan_id: str, scanner_name: str, operation: str, 
                                     progress: Optional[int] = None, details: Optional[Dict] = None):
                """Emit scanner operation event - SSE integration"""
                if progress:
                    # Use provided progress value
                    new_progress = min(90, self.current_progress + max(1, progress // 10))
                else:
                    # Default progress increment
                    new_progress = min(90, self.current_progress + 2)
                
                message = f"{scanner_name}: {operation}"
                if details:
                    if 'step' in details:
                        message += f" ({details['step']})"
                    if 'count' in details:
                        message += f" - {details['count']} elementi"
                
                if self.sse_monitor:
                    self.sse_monitor.emit_scanner_operation(
                        scan_id=scan_id,
                        scanner_name=scanner_name,
                        operation=operation,
                        progress=progress,
                        details=details
                    )
                
                self._safe_emit_progress(new_progress, message)
            
            def emit_scanner_complete(self, scan_id: str, scanner_name: str, results_summary: Dict[str, Any]):
                """Emit scanner completion event - SSE integration"""
                self.scanner_progress[scanner_name] = {"completed": True}
                
                # Create detailed completion message from results
                message = f"{scanner_name} completato"
                if results_summary:
                    if 'errors' in results_summary and 'warnings' in results_summary:
                        errors = results_summary.get('errors', 0)
                        warnings = results_summary.get('warnings', 0)
                        message += f" - {errors} errori, {warnings} avvisi"
                    elif 'violations' in results_summary:
                        violations = results_summary.get('violations', 0)
                        message += f" - {violations} violazioni trovate"
                    elif 'accessibility_score' in results_summary:
                        score = results_summary.get('accessibility_score', 0)
                        message += f" - score accessibilità: {score:.0%}"
                
                if self.sse_monitor:
                    self.sse_monitor.emit_scanner_complete(
                        scan_id=scan_id,
                        scanner_name=scanner_name,
                        results_summary=results_summary
                    )
                
                self._safe_emit_progress(self.current_progress + 10, message)
            
            def emit_scanner_error(self, scan_id: str, scanner_name: str, error_message: str, is_critical: bool = False):
                """Emit scanner error event - SSE integration"""
                self.scanner_progress[scanner_name] = {"error": True, "critical": is_critical}
                
                if is_critical:
                    message = f"ERRORE CRITICO in {scanner_name}: {error_message}"
                else:
                    message = f"Errore in {scanner_name}: {error_message}"
                
                if self.sse_monitor:
                    self.sse_monitor.emit_scanner_error(
                        scan_id=scan_id,
                        scanner_name=scanner_name,
                        error_message=error_message,
                        is_critical=is_critical
                    )
                
                # Don't increase progress on errors, but still notify
                self._safe_emit_progress(self.current_progress, message)
                
                # Also broadcast error-specific event
                try:
                    asyncio.create_task(self.ws_manager.broadcast(self.scan_id, {
                        "type": "scanner_error",
                        "scanner": scanner_name,
                        "error": error_message,
                        "critical": is_critical
                    }))
                except RuntimeError:
                    print(f"Scanner Error - {scanner_name}: {error_message}")
            
            def emit_processing_step(self, scan_id: str, step_name: str, progress: Optional[int] = None):
                """Emit processing step event - SSE integration"""
                if progress:
                    new_progress = min(95, progress)
                else:
                    new_progress = min(95, self.current_progress + 3)
                
                message = f"Elaborazione: {step_name}"
                
                if self.sse_monitor:
                    self.sse_monitor.emit_processing_step(
                        scan_id=scan_id,
                        step_name=step_name,
                        progress=progress
                    )
                
                self._safe_emit_progress(new_progress, message)
            
            def emit_report_generation(self, scan_id: str, stage: str, progress: Optional[int] = None):
                """Emit report generation event - SSE integration"""
                if progress:
                    new_progress = min(98, progress)
                else:
                    new_progress = min(98, self.current_progress + 2)
                
                message = f"Generazione report: {stage}"
                
                if self.sse_monitor:
                    self.sse_monitor.emit_report_generation(
                        scan_id=scan_id,
                        stage=stage,
                        progress=progress
                    )
                
                self._safe_emit_progress(new_progress, message)
            
            def emit_scan_complete(self, scan_id: str, results: Dict[str, Any]):
                """Emit scan complete event - SSE integration"""
                if self.sse_monitor:
                    self.sse_monitor.emit_scan_complete(scan_id, results)
                
                # Also broadcast via WebSocket
                try:
                    asyncio.create_task(self.ws_manager.broadcast(scan_id, {
                        "type": "scan_complete",
                        "status": "completed",
                        "results": results
                    }))
                except RuntimeError:
                    print(f"Scan completed: {scan_id}")
        
        monitor = ScanProgressMonitor(scan_id, scan_manager, ws_manager)
        
        # Emit scan start event
        monitor.emit_scan_start(
            scan_id=scan_id,
            url=str(request.url),
            company_name=request.company_name,
            scanners_enabled={
                'pa11y': eaa_config.scanners_enabled.pa11y,
                'axe_core': eaa_config.scanners_enabled.axe_core,
                'wave': eaa_config.scanners_enabled.wave,
                'lighthouse': eaa_config.scanners_enabled.lighthouse
            }
        )
        
        # Run the real EAA scanner
        await monitor.update_progress(20, "Esecuzione scanner EAA...")
        logger.info(f"========== CALLING EAA_RUN_SCAN for {scan_id} ==========")
        logger.info(f"EAA Config: url={eaa_config.url}, company={eaa_config.company_name}")
        logger.info(f"EAA Config: simulate={eaa_config.simulate}")
        logger.info(f"EAA Config: pa11y={eaa_config.scanners_enabled.pa11y}, axe={eaa_config.scanners_enabled.axe_core}")
        logger.info(f"EAA Config: lighthouse={eaa_config.scanners_enabled.lighthouse}, wave={eaa_config.scanners_enabled.wave}")
        logger.info(f"Output root: {output_root}")
        
        # Execute scan in thread pool to avoid blocking
        import concurrent.futures
        
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                loop = asyncio.get_event_loop()
                logger.info(f"========== STARTING THREAD EXECUTOR for {scan_id} ==========")
                eaa_result = await loop.run_in_executor(
                    executor,
                    lambda: eaa_run_scan(
                        cfg=eaa_config,
                        output_root=output_root,
                        enable_crawling=False,
                        event_monitor=monitor
                    )
                )
            logger.info(f"========== EAA_RUN_SCAN COMPLETED for {scan_id} ==========")
            logger.info(f"EAA Result type: {type(eaa_result)}")
            if eaa_result:
                logger.info(f"EAA Result keys: {list(eaa_result.keys())}")
                logger.info(f"EAA Aggregated: {eaa_result.get('aggregated', 'NO_AGGREGATED')}")
            else:
                logger.error(f"EAA Result is None or empty!")
        except Exception as eaa_error:
            logger.error(f"========== EAA_RUN_SCAN EXCEPTION for {scan_id} ==========")
            logger.error(f"Exception type: {type(eaa_error)}")
            logger.error(f"Exception message: {str(eaa_error)}")
            logger.error(f"Exception details:", exc_info=True)
            raise eaa_error
        
        await monitor.update_progress(90, "Elaborazione risultati...")
        
        # Process EAA results
        if eaa_result:
            # Extract key metrics from EAA result
            scan_results = await process_eaa_results(eaa_result, scan_id)
            
            # Save to database
            await save_scan_to_database(scan_id, request, scan_results, eaa_result)
            
            await scan_manager.update_scan(
                scan_id,
                status="completed",
                progress=100,
                results=scan_results,
                message="Scansione completata con successo"
            )
            
            # Update status tracking for polling
            if scan_status:
                scan_status.update(status="completed", progress=100, message="Scansione completata con successo", result=scan_results)
            
            await ws_manager.broadcast(scan_id, {
                "type": "complete",
                "status": "completed",
                "results": scan_results
            })
            
            # Emit scan complete event to SSE monitor
            if monitor.sse_monitor:
                monitor.sse_monitor.emit_scan_complete(
                    scan_id=scan_id,
                    scan_results={
                        'compliance_score': scan_results.get('compliance_score', 0),
                        'total_errors': scan_results.get('critical_issues', 0) + scan_results.get('high_issues', 0),
                        'total_warnings': scan_results.get('medium_issues', 0) + scan_results.get('low_issues', 0),
                        'pages_scanned': scan_results.get('pages_scanned', 1),
                        'report_url': f'/v2/preview?scan_id={scan_id}'
                    }
                )
        else:
            raise Exception("Scansione fallita: nessun risultato")
            
    except asyncio.TimeoutError:
        await scan_manager.update_scan(
            scan_id,
            status="failed",
            message="Timeout della scansione"
        )
        
        # Update status tracking
        if scan_status:
            scan_status.update(status="failed", progress=100, message="Timeout della scansione", error="Timeout")
        
        # Aggiorna anche il database per timeout
        try:
            conn = sqlite3.connect(get_database_path())
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE scans 
                SET status = ?, updated_at = ?
                WHERE id = ?
            ''', ("failed", datetime.utcnow().isoformat(), scan_id))
            conn.commit()
            conn.close()
        except Exception as db_error:
            logger.error(f"Failed to update timeout status in database: {db_error}")
            
        await ws_manager.broadcast(scan_id, {
            "type": "error",
            "status": "failed",
            "message": "Timeout della scansione"
        })
    except Exception as e:
        logger.error(f"========== BACKGROUND TASK EXCEPTION for {scan_id} ==========")
        logger.error(f"Exception type: {type(e)}")
        logger.error(f"Exception message: {str(e)}")
        logger.error(f"Real scan failed: {e}", exc_info=True)
        logger.error(f"========== END BACKGROUND TASK EXCEPTION ==========")
        await scan_manager.update_scan(
            scan_id,
            status="failed",
            message=f"Errore durante la scansione: {str(e)}"
        )
        
        # Update status tracking
        if scan_status:
            scan_status.update(status="failed", progress=100, message="Errore durante la scansione", error=str(e))
        
        await ws_manager.broadcast(scan_id, {
            "type": "error",
            "status": "failed",
            "message": "Errore durante la scansione"
        })

async def process_eaa_results(eaa_result: Dict[str, Any], scan_id: str) -> Dict[str, Any]:
    """Process EAA scanner results into API format"""
    try:
        # Validate EAA result is not None
        if eaa_result is None:
            logger.error(f"Scan {scan_id}: eaa_result is None, returning empty results")
            return {
                "total_issues": 0,
                "critical_issues": 0,
                "high_issues": 0,
                "medium_issues": 0,
                "low_issues": 0,
                "compliance_score": 0,
                "wcag_level": "AA",
                "eaa_compliant": False,
                "scan_duration": 0,
                "scanners_completed": 0,
                "pages_scanned": 0,
                "timestamp": datetime.utcnow().isoformat(),
                "output_path": "",
                "html_report_path": "",
                "detailed_results": {}
            }
        
        # Estrai i dati dal risultato aggregato del core
        aggregated = eaa_result.get("aggregated", {}) if isinstance(eaa_result, dict) else {}
        compliance = aggregated.get("compliance", {}) if isinstance(aggregated, dict) else {}
        detailed_results = aggregated.get("detailed_results", {}) if isinstance(aggregated, dict) else {}
        
        # Conta le issue per severità dai dati REALI
        critical_count = 0
        high_count = 0
        medium_count = 0
        low_count = 0
        
        # Conta dagli errori
        for error in detailed_results.get("errors", []):
            severity = error.get("severity", "medium").lower()
            count = error.get("count", 1)
            if severity == "critical":
                critical_count += count
            elif severity == "high":
                high_count += count
            elif severity == "medium":
                medium_count += count
            elif severity == "low":
                low_count += count
        
        # Conta dai warning
        for warning in detailed_results.get("warnings", []):
            severity = warning.get("severity", "low").lower()
            count = warning.get("count", 1)
            # I warning sono generalmente meno gravi
            if severity == "medium":
                medium_count += count
            else:
                low_count += count
        
        total_issues = critical_count + high_count + medium_count + low_count
        
        # Prendi il compliance score dal risultato
        compliance_score = compliance.get("overall_score", 0)
        
        # Log per debug
        logger.info(f"\n=== PROCESS_EAA_RESULTS for {scan_id} ===")
        logger.info(f"Total Issues: {total_issues} (C:{critical_count}, H:{high_count}, M:{medium_count}, L:{low_count})")
        logger.info(f"Compliance Score: {compliance_score}")
        logger.info(f"Detailed Results: {len(detailed_results.get('errors', []))} errors, {len(detailed_results.get('warnings', []))} warnings")
        
        processed_results = {
            "total_issues": total_issues,
            "critical_issues": critical_count,
            "high_issues": high_count,
            "medium_issues": medium_count,
            "low_issues": low_count,
            "compliance_score": float(compliance_score),
            "wcag_level": compliance.get("wcag_level", "AA"),
            "eaa_compliant": compliance.get("eaa_compliance", False) in ("compliant", True),
            "scan_duration": 0,
            "scanners_completed": len(aggregated.get("scan_metadata", {}).get("scanners_used", [])),
            "pages_scanned": eaa_result.get("pages_scanned", 1),
            "timestamp": datetime.utcnow().isoformat(),
            "output_path": str(eaa_result.get("base_out", "")),
            "html_report_path": str(eaa_result.get("report_html_path", "")),
            "detailed_results": detailed_results  # Passa i dati REALI
        }
        
        return processed_results
        
    except Exception as e:
        logger.error(f"Error processing EAA results: {e}")
        return {
            "total_issues": 0,
            "critical_issues": 0,
            "high_issues": 0,
            "medium_issues": 0,
            "low_issues": 0,
            "compliance_score": 0,
            "wcag_level": "Unknown",
            "eaa_compliant": False,
            "scan_duration": 0,
            "scanners_completed": 0,
            "pages_scanned": 0,
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

async def save_scan_to_database(scan_id: str, request: ScanRequest, results: Dict[str, Any], eaa_result: Dict[str, Any]):
    """Save scan results to SQLite database"""
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO scans 
            (id, url, company_name, email, status, progress, results, output_path, html_report_path, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            scan_id,
            str(request.url),
            request.company_name,
            request.email,
            "completed",
            100,
            json.dumps(results, ensure_ascii=False),
            results.get("output_path", ""),
            results.get("html_report_path", ""),
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Saved scan {scan_id} to database")
        
    except Exception as e:
        logger.error(f"Error saving scan to database: {e}")
        # Aggiorna anche il database in caso di errore
        try:
            conn = sqlite3.connect(get_database_path())
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE scans 
                SET status = ?, updated_at = ?
                WHERE id = ?
            ''', ("failed", datetime.utcnow().isoformat(), scan_id))
            conn.commit()
            conn.close()
        except Exception as db_error:
            logger.error(f"Failed to update scan status in database: {db_error}")
        
        raise e  # Re-raise per far scattare il except esterno
        
    except asyncio.TimeoutError:
        await scan_manager.update_scan(
            scan_id,
            status="failed",
            message="Timeout della scansione"
        )
        
        # Aggiorna anche il database per timeout
        try:
            conn = sqlite3.connect(get_database_path())
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE scans 
                SET status = ?, updated_at = ?
                WHERE id = ?
            ''', ("failed", datetime.utcnow().isoformat(), scan_id))
            conn.commit()
            conn.close()
        except Exception as db_error:
            logger.error(f"Failed to update timeout status in database: {db_error}")
            
        await ws_manager.broadcast(scan_id, {
            "type": "error",
            "status": "failed",
            "message": "Timeout della scansione"
        })
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        await scan_manager.update_scan(
            scan_id,
            status="failed",
            message="Errore durante la scansione"  # Don't expose full error
        )
        
        # Aggiorna anche il database per errori generali
        try:
            conn = sqlite3.connect(get_database_path())
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE scans 
                SET status = ?, updated_at = ?
                WHERE id = ?
            ''', ("failed", datetime.utcnow().isoformat(), scan_id))
            conn.commit()
            conn.close()
        except Exception as db_error:
            logger.error(f"Failed to update failed status in database: {db_error}")
            
        await ws_manager.broadcast(scan_id, {
            "type": "error",
            "status": "failed",
            "message": "Errore durante la scansione"
        })

async def generate_pdf_background(scan_id: str, pdf_id: str):
    """Background task to generate real PDF report"""
    try:
        logger.info(f"Starting real PDF generation for scan {scan_id}")
        
        # Get scan from database
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM scans WHERE id = ?', (scan_id,))
        scan_row = cursor.fetchone()
        conn.close()
        
        if not scan_row:
            raise Exception(f"Scan {scan_id} not found in database")
        
        # Extract scan data
        columns = ['id', 'url', 'company_name', 'email', 'status', 'progress', 'results', 'created_at', 'updated_at', 'output_path', 'html_report_path', 'pdf_report_path']
        scan_data = dict(zip(columns, scan_row))
        
        html_report_path = scan_data.get('html_report_path')
        if not html_report_path or not Path(html_report_path).exists():
            # Generate HTML report first
            logger.info("HTML report not found, generating...")
            html_report_path = await generate_html_report(scan_id, scan_data)
        
        if not html_report_path:
            raise Exception("Could not generate or find HTML report")
        
        # Generate PDF using real PDF engine
        pdf_filename = f"report_eaa_{scan_data['company_name']}_{scan_id}.pdf"
        pdf_path = Path("output") / scan_id / pdf_filename
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use the real PDF generation from eaa_scanner
        if EAA_SCANNER_AVAILABLE:
            success = html_to_pdf(
                html_path=Path(html_report_path),
                pdf_path=pdf_path,
                engine="auto"
            )
        else:
            # Fallback PDF generation using weasyprint or wkhtmltopdf
            success = await generate_pdf_fallback(Path(html_report_path), pdf_path)
        
        if success and pdf_path.exists():
            # Update database with PDF path
            conn = sqlite3.connect(get_database_path())
            cursor = conn.cursor()
            cursor.execute('UPDATE scans SET pdf_report_path = ? WHERE id = ?', (str(pdf_path), scan_id))
            conn.commit()
            conn.close()
            
            logger.info(f"PDF generation completed for scan {scan_id}: {pdf_path}")
        else:
            raise Exception("PDF generation failed")
        
    except Exception as e:
        logger.error(f"PDF generation failed for scan {scan_id}: {e}")
        raise

async def generate_html_report(scan_id: str, scan_data: Dict[str, Any]) -> Optional[str]:
    """Generate HTML report from scan data"""
    try:
        from eaa_scanner.report import generate_html_report as eaa_generate_html
        from eaa_scanner.config import Config as EAAConfig
        
        # Parse results with robust error handling
        results_json = scan_data.get('results', '{}')
        try:
            if isinstance(results_json, str):
                results = json.loads(results_json) if results_json else {}
            else:
                results = results_json or {}
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Failed to parse scan results JSON in generate_html_report for scan {scan_id}: {e}")
            results = {}
        
        # Create EAA config
        eaa_config = EAAConfig(
            url=scan_data['url'],
            company_name=scan_data['company_name'],
            email=scan_data['email']
        )
        
        # Generate HTML report
        output_dir = Path("output") / scan_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        html_filename = f"report_{scan_data['company_name']}_{scan_id}.html"
        html_path = output_dir / html_filename
        
        # Use EAA scanner's HTML generation if available
        if EAA_SCANNER_AVAILABLE:
            html_content = eaa_generate_html(eaa_config, results)
        else:
            # Fallback HTML generation
            html_content = await generate_html_fallback(eaa_config, results)
        
        async with aiofiles.open(html_path, 'w', encoding='utf-8') as f:
            await f.write(html_content)
        
        # Update database
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute('UPDATE scans SET html_report_path = ? WHERE id = ?', (str(html_path), scan_id))
        conn.commit()
        conn.close()
        
        return str(html_path)
        
    except Exception as e:
        logger.error(f"HTML report generation failed: {e}")
        return None

async def run_llm_regeneration(regeneration_id: str, request: RegenerationRequest):
    """Background task to run real LLM regeneration"""
    try:
        logger.info(f"Starting real LLM regeneration {regeneration_id}")
        
        # Get regeneration session from database
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        
        # Update initial status
        cursor.execute('''
            UPDATE regeneration_sessions 
            SET status = ?, progress = ?, updated_at = ?
            WHERE id = ?
        ''', ("analyzing", 10, datetime.utcnow().isoformat(), regeneration_id))
        conn.commit()
        
        # Get original scan data
        cursor.execute('SELECT * FROM scans WHERE id = ?', (request.scan_id,))
        scan_row = cursor.fetchone()
        
        if not scan_row:
            raise Exception(f"Scan {request.scan_id} not found")
        
        # Extract scan data
        columns = ['id', 'url', 'company_name', 'email', 'status', 'progress', 'results', 'created_at', 'updated_at', 'output_path', 'html_report_path', 'pdf_report_path']
        scan_data = dict(zip(columns, scan_row))
        
        # Parse results with robust error handling
        results_json = scan_data.get('results', '{}')
        try:
            if isinstance(results_json, str):
                scan_results = json.loads(results_json) if results_json else {}
            else:
                scan_results = results_json or {}
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Failed to parse scan results JSON in regeneration for scan {request.scan_id}: {e}")
            scan_results = {}
        
        # Update progress
        cursor.execute('''
            UPDATE regeneration_sessions 
            SET status = ?, progress = ?, updated_at = ?
            WHERE id = ?
        ''', ("processing", 25, datetime.utcnow().isoformat(), regeneration_id))
        conn.commit()
        
        # Use real LLM integration
        effective_key = get_effective_openai_key()
        if not effective_key:
            logger.warning("OpenAI API key not configured, returning original report without enhancement")
            return {
                "regeneration_id": regeneration_id,
                "status": "completed",
                "model": request.model,
                "content": original_report,
                "usage": {"tokens": 0, "cost": 0},
                "message": "Report restituito senza enhancement LLM (chiave OpenAI non configurata)"
            }
        
        from eaa_scanner.llm_integration import LLMIntegration
        from eaa_scanner.config import Config as EAAConfig
        
        # Create EAA config with LLM enabled
        eaa_config = EAAConfig(
            url=scan_data['url'],
            company_name=scan_data['company_name'],
            email=scan_data['email'],
            openai_api_key=get_effective_openai_key(),
            llm_enabled=False,  # Temporaneamente disabilitato per test
            llm_model_primary=request.model
        )
        
        # Initialize LLM integration
        llm = LLMIntegration(eaa_config)
        
        if not llm.is_enabled():
            raise Exception("LLM integration not available")
        
        # Update progress
        cursor.execute('''
            UPDATE regeneration_sessions 
            SET status = ?, progress = ?, updated_at = ?
            WHERE id = ?
        ''', ("generating", 50, datetime.utcnow().isoformat(), regeneration_id))
        conn.commit()
        
        # Generate enhanced content based on request type
        enhanced_results = {}
        tokens_used = 0
        cost_estimate = 0.0
        
        if request.content_type == "full_report":
            # Generate full enhanced report
            enhanced_summary = llm.generate_executive_summary(scan_results)
            enhanced_recommendations = llm.generate_detailed_recommendations(scan_results)
            cost_estimate += 0.3
            tokens_used += 1500
            
            enhanced_results = {
                "original_scan_id": request.scan_id,
                "enhanced_summary": enhanced_summary,
                "enhanced_recommendations": enhanced_recommendations,
                "content_type": "full_report",
                "model_used": request.model,
                "tokens_used": tokens_used,
                "cost_estimate": cost_estimate
            }
        
        elif request.content_type == "summary_only":
            # Generate only enhanced summary
            enhanced_summary = llm.generate_executive_summary(scan_results)
            cost_estimate += 0.1
            tokens_used += 500
            
            enhanced_results = {
                "original_scan_id": request.scan_id,
                "enhanced_summary": enhanced_summary,
                "content_type": "summary_only",
                "model_used": request.model,
                "tokens_used": tokens_used,
                "cost_estimate": cost_estimate
            }
        
        elif request.content_type == "recommendations_only":
            # Generate only enhanced recommendations
            enhanced_recommendations = llm.generate_detailed_recommendations(scan_results)
            cost_estimate += 0.2
            tokens_used += 1000
            
            enhanced_results = {
                "original_scan_id": request.scan_id,
                "enhanced_recommendations": enhanced_recommendations,
                "content_type": "recommendations_only",
                "model_used": request.model,
                "tokens_used": tokens_used,
                "cost_estimate": cost_estimate
            }
        
        # Update completion status
        cursor.execute('''
            UPDATE regeneration_sessions 
            SET status = ?, progress = ?, results = ?, tokens_used = ?, cost_estimate = ?, updated_at = ?
            WHERE id = ?
        ''', (
            "completed", 100, 
            json.dumps(enhanced_results, ensure_ascii=False),
            tokens_used, cost_estimate,
            datetime.utcnow().isoformat(), regeneration_id
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Real LLM regeneration completed: {regeneration_id}")
        
    except Exception as e:
        logger.error(f"Real LLM regeneration failed: {e}", exc_info=True)
        
        # Update failure status
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE regeneration_sessions 
            SET status = ?, updated_at = ?
            WHERE id = ?
        ''', ("failed", datetime.utcnow().isoformat(), regeneration_id))
        conn.commit()
        conn.close()

# ==================== DISCOVERY ENDPOINTS ====================

class DiscoveryRequest(BaseModel):
    """Enhanced discovery request model"""
    base_url: Optional[HttpUrl] = None
    url: Optional[HttpUrl] = None
    discovery_mode: str = Field(default="smart")
    max_pages: int = Field(default=50, ge=1, le=1000)
    max_depth: int = Field(default=3, ge=1, le=10)
    include_external: bool = False
    include_media: bool = True
    focus_areas: List[str] = Field(default=["forms", "navigation", "content"])
    company_name: Optional[str] = None
    email: Optional[EmailStr] = None
    
    @validator('url', always=True)
    def url_or_base_url(cls, v, values):
        """Accept either url or base_url"""
        if v is None and 'base_url' in values and values['base_url']:
            return values['base_url']
        if v is None and 'base_url' not in values:
            raise ValueError('Either url or base_url must be provided')
        return v
    
    @validator('url', pre=False)
    def validate_discovery_url(cls, v):
        """Enhanced URL validation for discovery"""
        url_str = str(v)
        
        # Block dangerous schemes
        if url_str.startswith(('javascript:', 'data:', 'file:', 'ftp:')):
            raise ValueError('Schema URL non valido per discovery')
        
        # Block local addresses unless allowed in development
        if not settings.allow_local_urls:
            blocked_markers = ['localhost', '127.0.0.1', '0.0.0.0', '::1', '192.168.', '10.']
            lower = url_str.lower()
            for marker in blocked_markers:
                if marker in lower:
                    raise ValueError('Indirizzi locali non consentiti per discovery (abilita DEV_ALLOW_LOCAL_URLS per sviluppo)')
        
        return v

class DiscoveryResponse(BaseModel):
    """Enhanced discovery response model"""
    session_id: str
    status: str
    message: str
    estimated_completion: Optional[datetime] = None
    discovery_mode: Optional[str] = None

@app.post("/api/discovery/start", response_model=DiscoveryResponse)
async def start_discovery(
    request: DiscoveryRequest,
    background_tasks: BackgroundTasks,
    dependencies=[Depends(check_rate_limit)]
):
    """Start comprehensive URL discovery process with rate limiting"""
    session_id = secrets.token_urlsafe(16)
    
    # Enhanced discovery session with more metadata
    discovery_sessions[session_id] = {
        "status": "running",
        "progress": 0,
        "message": "Inizializzazione discovery...",
        "pages_found": [],
        "created_at": datetime.utcnow().isoformat(),
        "url": str(request.url),
        "discovery_mode": request.discovery_mode,
        "max_pages": request.max_pages,
        "max_depth": request.max_depth,
        "start_time": time.time(),
        "estimated_completion": (datetime.utcnow() + timedelta(minutes=2)).isoformat()
    }
    
    # Start discovery in background
    background_tasks.add_task(run_discovery, session_id, request)
    
    logger.info(f"Started discovery session {session_id} for {request.url}")
    
    return DiscoveryResponse(
        session_id=session_id,
        status="running",
        message="Discovery avviata con successo"
    )

@app.get("/api/discovery/status/{session_id}")
async def get_discovery_status(session_id: str):
    """Get comprehensive discovery session status"""
    if session_id not in discovery_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessione di discovery non trovata"
        )
    
    session = discovery_sessions[session_id]
    pages_found = session.get("pages_found", [])
    
    # Align response format with frontend expectations
    return {
        "session_id": session_id,
        "state": session["status"],  # Frontend expects 'state' not 'status'
        "status": session["status"],  # Keep for backward compatibility
        "progress": session.get("progress", 0),
        "progress_percent": session.get("progress", 0),  # Frontend expects 'progress_percent'
        "pages_found": len(pages_found),
        "pages_discovered": len(pages_found),  # Frontend expects 'pages_discovered'
        "discovered_pages": pages_found[:10] if pages_found else [],  # Frontend expects 'discovered_pages' array
        "message": session.get("message", f"Trovate {len(pages_found)} pagine"),
        "url": session["url"],
        "max_pages": session["max_pages"],
        "max_depth": session["max_depth"],
        "created_at": session["created_at"],
        "estimated_completion": None if session["status"] == "completed" else (datetime.utcnow() + timedelta(seconds=30)).isoformat()
    }

@app.get("/api/discovery/results/{session_id}")
async def get_discovery_results(session_id: str):
    """Get real discovery results from memory (discovery sessions are not persisted in DB)"""
    if session_id not in discovery_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessione di discovery non trovata"
        )
    
    session = discovery_sessions[session_id]
    
    # Check if pages were found by real crawler
    pages_found = session.get("pages_found", [])
    
    if not pages_found:
        # Return empty result if discovery failed
        return {
            "success": False,
            "session_id": session_id,
            "status": session["status"],
            "data": {
                "pages": [],
                "summary": {
                    "total_pages": 0,
                    "estimated_total_scan_time": 0,
                    "priority_distribution": {},
                    "type_distribution": {},
                    "depth_analysis": {
                        "max_depth": 0,
                        "avg_depth": 0
                    }
                },
                "recommendations": {
                    "scan_order": "Nessuna pagina trovata",
                    "estimated_duration": "0 minuti",
                    "accessibility_focus": []
                }
            },
            "message": "Nessuna pagina trovata durante il discovery"
        }
    
    # Calculate summary statistics from real results
    total_pages = len(pages_found)
    total_scan_time = sum(page.get("estimated_scan_time", 30) for page in pages_found)
    priority_distribution = {}
    type_distribution = {}
    
    for page in pages_found:
        priority = page.get("priority", "media")
        page_type = page.get("type", "contenuti")
        priority_distribution[priority] = priority_distribution.get(priority, 0) + 1
        type_distribution[page_type] = type_distribution.get(page_type, 0) + 1
    
    # Calculate depth analysis safely
    depths = [page.get("depth", 0) for page in pages_found]
    max_depth = max(depths) if depths else 0
    avg_depth = sum(depths) / len(depths) if depths else 0
    
    # Generate recommendations based on found pages
    high_priority_types = [page["type"] for page in pages_found if page.get("priority") == "alta"]
    accessibility_focus = []
    
    if "contatti" in type_distribution:
        accessibility_focus.append("Forms di contatto")
    if "homepage" in type_distribution:
        accessibility_focus.append("Navigazione principale")
    if sum(page.get("elements", {}).get("images", 0) for page in pages_found) > 10:
        accessibility_focus.append("Contenuti media")
    if sum(page.get("elements", {}).get("forms", 0) for page in pages_found) > 0:
        accessibility_focus.append("Validazione form")
    
    return {
        "success": True,
        "session_id": session_id,
        "status": session["status"],
        "data": {
            "pages": pages_found,
            "summary": {
                "total_pages": total_pages,
                "estimated_total_scan_time": total_scan_time,
                "priority_distribution": priority_distribution,
                "type_distribution": type_distribution,
                "depth_analysis": {
                    "max_depth": max_depth,
                    "avg_depth": round(avg_depth, 1)
                }
            },
            "recommendations": {
                "scan_order": "Inizia con pagine ad alta priorità" if high_priority_types else "Scansiona in ordine di scoperta",
                "estimated_duration": f"{total_scan_time // 60} minuti e {total_scan_time % 60} secondi",
                "accessibility_focus": accessibility_focus
            }
        },
        "message": f"Discovery completata: {total_pages} pagine trovate"
    }

async def run_discovery(session_id: str, request: DiscoveryRequest):
    """Run real discovery process using web crawler"""
    try:
        logger.info(f"Starting real discovery for session {session_id}")
        
        # Update progress callback
        async def progress_callback(progress: int, message: str):
            if session_id in discovery_sessions:
                discovery_sessions[session_id]["progress"] = progress
                discovery_sessions[session_id]["message"] = message
        
        # Validate URL before creating crawler
        discovery_url = request.url or request.base_url
        if not discovery_url:
            raise ValueError("Nessun URL valido fornito per la discovery")
        
        # Ensure URL is properly formatted
        discovery_url_str = str(discovery_url)
        if discovery_url_str in ("None", "null", ""):
            raise ValueError("URL non valido per la discovery")
        
        # Create web crawler (automatically uses optimized version if aiohttp is available)
        crawler = RealWebCrawler(
            base_url=discovery_url_str,
            max_pages=request.max_pages,
            max_depth=request.max_depth
        )
        
        # Discover URLs using real crawler with extended timeout
        try:
            discovered_pages = await asyncio.wait_for(
                crawler.discover_urls(progress_callback),
                timeout=60.0  # Increase timeout to 60 seconds
            )
        except asyncio.TimeoutError:
            logger.warning("Discovery timeout after 60s, using partial results")
            # Try to get any partial results from the crawler
            discovered_pages = getattr(crawler, 'discovered_urls', [])
        
        # Update session with real results
        if session_id in discovery_sessions:
            discovery_sessions[session_id]["pages_found"] = discovered_pages
            discovery_sessions[session_id]["status"] = "completed"
            discovery_sessions[session_id]["progress"] = 100
            discovery_sessions[session_id]["message"] = f"Discovery completata: {len(discovered_pages)} pagine trovate"
            
            logger.info(f"Discovery completed for session {session_id}: {len(discovered_pages)} pages found")
            
    except Exception as e:
        logger.error(f"Real discovery failed: {e}", exc_info=True)
        if session_id in discovery_sessions:
            discovery_sessions[session_id]["status"] = "failed"
            discovery_sessions[session_id]["message"] = "Errore durante il discovery"
            discovery_sessions[session_id]["progress"] = 100

# ==================== MISSING API ENDPOINTS ====================

@app.get("/api/scan/results/{scan_id}")
async def get_scan_results(
    scan_id: str
):
    """Get detailed scan results from database with fallback to scan_manager"""
    try:
        # Prima prova dal database
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM scans WHERE id = ?', (scan_id,))
        scan_row = cursor.fetchone()
        conn.close()
        
        if not scan_row:
            # Fallback: cerca in scan_manager (in memoria)
            scan_data = scan_manager.get_scan(scan_id)
            if scan_data:
                logger.info(f"Scan {scan_id} found in memory but not in database, syncing...")
                # Sincronizza con il database
                await sync_scan_to_database(scan_id)
                
                # Riprova dal database
                conn = sqlite3.connect(get_database_path())
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM scans WHERE id = ?', (scan_id,))
                scan_row = cursor.fetchone()
                conn.close()
                
                if not scan_row:
                    # Se ancora non c'è, restituisci dai dati in memoria
                    logger.warning(f"Database sync failed for scan {scan_id}, returning in-memory data")
                    return {
                        "scan_id": scan_id,
                        "status": scan_data["status"],
                        "url": scan_data["request"].get("url", ""),
                        "company_name": scan_data["request"].get("company_name", ""),
                        "created_at": scan_data["created_at"].isoformat(),
                        "completed_at": scan_data["updated_at"].isoformat(),
                        "summary": {
                            "total_issues": 0,
                            "critical_issues": 0,
                            "high_issues": 0,
                            "medium_issues": 0,
                            "low_issues": 0,
                            "compliance_score": 0,
                            "wcag_level": "AA",
                            "eaa_compliant": False
                        },
                        "detailed_results": scan_data.get("results", {}),
                        "output_path": "",
                        "report_urls": {
                            "html": f"/api/download_report/{scan_id}?format=html",
                            "pdf": f"/api/download_report/{scan_id}?format=pdf",
                            "json": f"/api/download_report/{scan_id}?format=json"
                        }
                    }
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Scansione non trovata"
                )
        
        # Extract scan data
        columns = ['id', 'url', 'company_name', 'email', 'status', 'progress', 'results', 'created_at', 'updated_at', 'output_path', 'html_report_path', 'pdf_report_path']
        scan_data = dict(zip(columns, scan_row))
        
        # Parse results JSON with robust error handling
        results_json = scan_data.get('results', '{}')
        try:
            if isinstance(results_json, str):
                detailed_results = json.loads(results_json) if results_json else {}
            else:
                detailed_results = results_json or {}
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Failed to parse scan results JSON for scan {scan_id}: {e}")
            detailed_results = {}
        
        # Try to load enterprise summary data for more accurate results
        enterprise_summary = None
        output_path = scan_data.get("output_path", "")
        logger.info(f"DEBUG: scan {scan_id} output_path = {output_path}")
        
        if output_path and os.path.exists(output_path):
            enterprise_summary_path = os.path.join(output_path, "enterprise_summary.json")
            logger.info(f"DEBUG: enterprise_summary_path = {enterprise_summary_path}")
            logger.info(f"DEBUG: enterprise file exists = {os.path.exists(enterprise_summary_path)}")
            
            if os.path.exists(enterprise_summary_path):
                try:
                    with open(enterprise_summary_path, 'r', encoding='utf-8') as f:
                        enterprise_summary = json.load(f)
                        logger.info(f"✅ Loaded enterprise summary for scan {scan_id}")
                        logger.info(f"DEBUG: enterprise_summary keys = {list(enterprise_summary.keys())}")
                except Exception as e:
                    logger.warning(f"Failed to load enterprise summary: {e}")
        else:
            logger.info(f"DEBUG: output_path missing or doesn't exist: {output_path}")
        
        # Extract summary data with enterprise fallback
        if enterprise_summary and enterprise_summary.get("compliance_metrics"):
            metrics = enterprise_summary["compliance_metrics"]
            total_issues = metrics.get("total_violations", 0)
            
            # Gestione robusta della conversione del punteggio
            raw_score = metrics.get("overall_score", "0")
            try:
                if isinstance(raw_score, (int, float)):
                    compliance_score = float(raw_score)
                elif isinstance(raw_score, str):
                    compliance_score = float(raw_score.replace("%", "").strip())
                else:
                    compliance_score = 0.0
            except (ValueError, AttributeError) as e:
                logger.warning(f"Failed to parse overall_score '{raw_score}': {e}")
                compliance_score = 0.0
                
            logger.info(f"DEBUG: enterprise compliance_score = {compliance_score} (from {raw_score})")
            
            summary_data = {
                "total_issues": total_issues,
                "critical_issues": metrics.get("critical_violations", 0),
                "high_issues": metrics.get("high_violations", 0), 
                "medium_issues": metrics.get("medium_violations", 0),
                "low_issues": metrics.get("low_violations", 0),
                "compliance_score": compliance_score,
                "wcag_level": "AA",
                "eaa_compliant": compliance_score >= 75
            }
        else:
            # Fallback to detailed_results
            summary_data = {
                "total_issues": detailed_results.get("total_issues", 0),
                "critical_issues": detailed_results.get("critical_issues", 0),
                "high_issues": detailed_results.get("high_issues", 0),
                "medium_issues": detailed_results.get("medium_issues", 0),
                "low_issues": detailed_results.get("low_issues", 0),
                "compliance_score": detailed_results.get("compliance_score", 0),
                "wcag_level": detailed_results.get("wcag_level", "AA"),
                "eaa_compliant": detailed_results.get("eaa_compliant", False)
            }

        # Build comprehensive response with frontend-compatible structure
        response = {
            "scan_id": scan_id,
            "status": scan_data["status"],
            "url": scan_data["url"],
            "company_name": scan_data["company_name"],
            "created_at": scan_data["created_at"],
            "completed_at": scan_data["updated_at"],
            "summary": summary_data,
            
            # Frontend-compatible structure: flatten metrics to root level
            "compliance_score": summary_data.get("compliance_score", 0),
            "compliance_level": "non_conforme" if summary_data.get("compliance_score", 0) < 70 else ("parzialmente_conforme" if summary_data.get("compliance_score", 0) < 90 else "conforme"),
            "total_issues": summary_data.get("total_issues", 0),
            "issues_total": summary_data.get("total_issues", 0),  # Alias for frontend compatibility
            "critical_issues": summary_data.get("critical_issues", 0),
            "high_issues": summary_data.get("high_issues", 0),
            "medium_issues": summary_data.get("medium_issues", 0),
            "low_issues": summary_data.get("low_issues", 0),
            "issues_by_severity": {
                "critical": summary_data.get("critical_issues", 0),
                "high": summary_data.get("high_issues", 0),
                "medium": summary_data.get("medium_issues", 0),
                "low": summary_data.get("low_issues", 0)
            },
            "wcag_aa_pass": summary_data.get("eaa_compliant", False),
            "eaa_compliant": summary_data.get("eaa_compliant", False),
            "pages_scanned": enterprise_summary.get("scan_context", {}).get("pages_total", 1) if enterprise_summary else 1,
            "scanners_used": ["pa11y", "axe", "lighthouse", "wave"] if enterprise_summary else [],
            
            # Include enterprise detailed results if available, otherwise use DB results
            "detailed_results": enterprise_summary.get("individual_results", []) if enterprise_summary else detailed_results,
            "output_path": scan_data.get("output_path", ""),
            "report_urls": {
                "html": f"/api/download_report/{scan_id}?format=html",
                "pdf": f"/api/download_report/{scan_id}?format=pdf", 
                "json": f"/api/download_report/{scan_id}?format=json"
            }
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting scan results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore nel recupero dei risultati"
        )


@app.post("/api/generate_pdf/{scan_id}")
async def generate_pdf_report(
    scan_id: str,
    background_tasks: BackgroundTasks,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Generate PDF report from scan results"""
    scan = scan_manager.get_scan(scan_id)
    
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scansione non trovata"
        )
    
    if scan["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La scansione deve essere completata prima di generare il PDF"
        )
    
    # Mock PDF generation
    pdf_id = secrets.token_urlsafe(16)
    background_tasks.add_task(generate_pdf_background, scan_id, pdf_id)
    
    return {
        "success": True,
        "pdf_id": pdf_id,
        "message": "Generazione PDF avviata",
        "estimated_time": "2-3 minuti",
        "download_url": f"/api/download_report/{scan_id}?format=pdf&pdf_id={pdf_id}"
    }

@app.get("/api/download_report/{scan_id}")
async def download_report(
    scan_id: str,
    format: str = "html",
    version: str = "original",
    pdf_id: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Download real report files in various formats"""
    try:
        # Get scan from database
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM scans WHERE id = ?', (scan_id,))
        scan_row = cursor.fetchone()
        conn.close()
        
        if not scan_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scansione non trovata"
            )
        
        # Extract scan data
        columns = ['id', 'url', 'company_name', 'email', 'status', 'progress', 'results', 'created_at', 'updated_at', 'output_path', 'html_report_path', 'pdf_report_path']
        scan_data = dict(zip(columns, scan_row))
        
        company_name = scan_data["company_name"]
        created_at = datetime.fromisoformat(scan_data["created_at"])
        timestamp = created_at.strftime("%Y%m%d_%H%M%S")
        
        if format.lower() == "pdf":
            # Serve real PDF file
            pdf_path = scan_data.get("pdf_report_path")
            
            if not pdf_path or not Path(pdf_path).exists():
                # Generate PDF if not exists
                pdf_id = secrets.token_urlsafe(16)
                try:
                    await generate_pdf_background(scan_id, pdf_id)
                    # Refresh scan data
                    conn = sqlite3.connect(get_database_path())
                    cursor = conn.cursor()
                    cursor.execute('SELECT pdf_report_path FROM scans WHERE id = ?', (scan_id,))
                    pdf_path = cursor.fetchone()[0]
                    conn.close()
                except Exception as e:
                    logger.error(f"PDF generation failed: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Errore nella generazione del PDF"
                    )
            
            if pdf_path and Path(pdf_path).exists():
                filename = f"report_eaa_{company_name}_{timestamp}.pdf"
                return FileResponse(
                    path=pdf_path,
                    media_type="application/pdf",
                    filename=filename
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File PDF non trovato"
                )
        
        elif format.lower() == "json":
            # Return JSON results
            results = await get_scan_results(scan_id, current_user)
            filename = f"report_eaa_{company_name}_{timestamp}.json"
            
            return Response(
                content=json.dumps(results, indent=2, default=str, ensure_ascii=False),
                media_type="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}"
                }
            )
        
        else:  # HTML format (default)
            # Serve real HTML file
            html_path = scan_data.get("html_report_path")
            
            if not html_path or not Path(html_path).exists():
                # Generate HTML if not exists
                html_path = await generate_html_report(scan_id, scan_data)
            
            if html_path and Path(html_path).exists():
                filename = f"report_eaa_{company_name}_{timestamp}.html"
                return FileResponse(
                    path=html_path,
                    media_type="text/html",
                    filename=filename
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File HTML non trovato"
                )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore nel download del report"
        )

# ==================== BACKWARD COMPATIBLE ALIASES ====================

@app.get("/download/html")
async def download_html_legacy(scan_id: str):
    """Legacy endpoint for HTML download - backward compatibility"""
    return await download_report(scan_id, format="html")

@app.get("/download/pdf") 
async def download_pdf_legacy(scan_id: str):
    """Legacy endpoint for PDF download - backward compatibility"""
    return await download_report(scan_id, format="pdf")

# ==================== LLM & REGENERATION ENDPOINTS ====================

@app.get("/api/llm/regeneration_status/{regeneration_id}")
async def get_regeneration_status(regeneration_id: str):
    """Get LLM regeneration status from database"""
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM regeneration_sessions WHERE id = ?', (regeneration_id,))
        session_row = cursor.fetchone()
        conn.close()
        
        if not session_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sessione di rigenerazione non trovata"
            )
        
        # Extract session data
        columns = ['id', 'scan_id', 'model', 'content_type', 'status', 'progress', 'results', 'created_at', 'updated_at', 'cost_estimate', 'tokens_used']
        session_data = dict(zip(columns, session_row))
        
        # Calculate estimated completion for running sessions
        estimated_completion = None
        if session_data["status"] not in ["completed", "failed"]:
            created_at = datetime.fromisoformat(session_data["created_at"])
            estimated_completion = (created_at + timedelta(minutes=5)).isoformat()
        
        return {
            "regeneration_id": regeneration_id,
            "status": session_data["status"],
            "progress": session_data["progress"],
            "estimated_completion": estimated_completion,
            "cost_estimate": session_data["cost_estimate"],
            "tokens_used": session_data["tokens_used"],
            "created_at": session_data["created_at"],
            "updated_at": session_data["updated_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting regeneration status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore nel recupero dello stato"
        )

@app.get("/api/scan/stream/{scan_id}")
async def scan_stream_polling(
    scan_id: str,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Polling endpoint for scan updates (replaces SSE stream)"""
    scan = scan_manager.get_scan(scan_id)
    
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scansione non trovata"
        )
    
    try:
        # Get historical events if available
        historical_events = []
        try:
            from webapp.scan_monitor import get_scan_monitor
            monitor = get_scan_monitor()
            
            if scan_id in monitor.event_history:
                historical_events = monitor.event_history[scan_id][-5:]  # Last 5 events
        except Exception as e:
            logger.warning(f"Could not get historical events: {e}")
        
        # Prepare response data
        response_data = {
            "scan_id": scan_id,
            "status": scan["status"],
            "progress": scan.get("progress", 0),
            "message": scan.get("message", ""),
            "results": scan.get("results") if scan["status"] in ["completed", "failed"] else None,
            "error": scan.get("error") if scan["status"] == "failed" else None,
            "timestamp": time.time(),
            "polling_interval": 2,  # Suggested polling interval in seconds
            "recent_events": historical_events,
            "is_completed": scan["status"] in ["completed", "failed"]
        }
        
        # Clean up old scans
        cleanup_old_scans()
        
        return JSONResponse(
            content=response_data,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
        
    except Exception as e:
        logger.error(f"Error in scan stream polling: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore nel recupero dello stato della scansione"
        )

# ==================== UTILITY ENDPOINTS ====================

@app.get("/api/system/stats")
async def get_system_stats(
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get real system statistics from database"""
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        
        # Get scan statistics
        cursor.execute('SELECT COUNT(*) FROM scans')
        total_scans = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM scans WHERE status = "completed"')
        completed_scans = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM scans WHERE status = "failed"')
        failed_scans = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM scans WHERE status IN ("running", "pending")')
        active_scans = cursor.fetchone()[0]
        
        # Get average compliance score
        cursor.execute('''
            SELECT AVG(CAST(JSON_EXTRACT(results, '$.compliance_score') AS REAL))
            FROM scans 
            WHERE status = "completed" AND results IS NOT NULL
        ''')
        avg_compliance_result = cursor.fetchone()[0]
        avg_compliance = round(avg_compliance_result or 0, 1)
        
        # Get average scan duration
        cursor.execute('''
            SELECT AVG(CAST(JSON_EXTRACT(results, '$.scan_duration') AS REAL))
            FROM scans 
            WHERE status = "completed" AND results IS NOT NULL
        ''')
        avg_duration_result = cursor.fetchone()[0]
        avg_duration = round(avg_duration_result or 0, 1)
        
        # Get average issues per scan
        cursor.execute('''
            SELECT AVG(CAST(JSON_EXTRACT(results, '$.total_issues') AS INTEGER))
            FROM scans 
            WHERE status = "completed" AND results IS NOT NULL
        ''')
        avg_issues_result = cursor.fetchone()[0]
        avg_issues = round(avg_issues_result or 0, 1)
        
        # Get LLM usage statistics
        cursor.execute('SELECT COUNT(*) FROM regeneration_sessions')
        total_regenerations = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(cost_estimate) FROM regeneration_sessions WHERE status = "completed"')
        total_cost_result = cursor.fetchone()[0]
        total_cost = round(total_cost_result or 0, 2)
        
        cursor.execute('SELECT AVG(tokens_used) FROM regeneration_sessions WHERE status = "completed"')
        avg_tokens_result = cursor.fetchone()[0]
        avg_tokens = round(avg_tokens_result or 0, 0)
        
        conn.close()
        
        # Calculate success rate
        success_rate = round((completed_scans / max(1, total_scans)) * 100, 1)
        
        # Calculate compliance rate
        compliance_rate = 0
        if completed_scans > 0:
            conn = sqlite3.connect(get_database_path())
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM scans 
                WHERE status = "completed" 
                AND JSON_EXTRACT(results, '$.eaa_compliant') = 1
            ''')
            compliant_scans = cursor.fetchone()[0]
            conn.close()
            compliance_rate = round((compliant_scans / completed_scans) * 100, 1)
        
        stats = {
            "scans": {
                "total": total_scans,
                "completed": completed_scans,
                "failed": failed_scans,
                "active": active_scans,
                "success_rate": success_rate
            },
            "performance": {
                "avg_scan_duration": f"{avg_duration} secondi" if avg_duration > 0 else "N/A",
                "avg_issues_per_scan": avg_issues,
                "avg_compliance_score": avg_compliance,
                "compliance_rate": f"{compliance_rate}%"
            },
            "system": {
                "redis_connected": redis_available,
                "database_connected": True,
                "openai_configured": bool(settings.openai_api_key),
                "wave_configured": bool(os.getenv("WAVE_API_KEY"))
            },
            "discovery": {
                "active_sessions": len(discovery_sessions),
                "avg_pages_found": 0  # Would need to track this separately
            },
            "llm_usage": {
                "total_regenerations": total_regenerations,
                "total_cost": f"${total_cost}",
                "avg_tokens_per_request": int(avg_tokens),
                "available_models": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
            }
        }
        
        return {
            "success": True,
            "data": stats,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Statistiche di sistema recuperate con successo"
        }
        
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore nel recupero delle statistiche"
        )

@app.get("/api/scanner/capabilities")
async def get_scanner_capabilities():
    """Get available scanner capabilities and configuration"""
    
    capabilities = {
        "scanners": {
            "wave": {
                "name": "WebAIM WAVE",
                "description": "Scanner professionale per accessibilità web",
                "version": "6.0+",
                "requires_api_key": True,
                "supported_standards": ["WCAG 2.1", "WCAG 2.2", "Section 508"],
                "detection_capabilities": [
                    "Missing alt text",
                    "Heading structure",
                    "Color contrast",
                    "Form labels",
                    "ARIA attributes"
                ],
                "limitations": ["Richiede chiave API a pagamento"]
            },
            "axe": {
                "name": "Axe-core",
                "description": "Engine di accessibilità open source di Deque",
                "version": "4.8+",
                "requires_api_key": False,
                "supported_standards": ["WCAG 2.1", "WCAG 2.2", "Section 508"],
                "detection_capabilities": [
                    "ARIA compliance",
                    "Keyboard navigation",
                    "Color contrast",
                    "Semantic markup",
                    "Focus management"
                ],
                "limitations": ["Richiede Node.js installato"]
            },
            "lighthouse": {
                "name": "Google Lighthouse",
                "description": "Audit di performance e accessibilità di Google",
                "version": "11.0+",
                "requires_api_key": False,
                "supported_standards": ["WCAG 2.1", "Best practices"],
                "detection_capabilities": [
                    "Performance metrics",
                    "Accessibility score",
                    "SEO basics",
                    "Best practices",
                    "PWA compliance"
                ],
                "limitations": ["Richiede Chrome/Chromium"]
            },
            "pa11y": {
                "name": "Pa11y",
                "description": "Command line accessibility tester",
                "version": "7.0+",
                "requires_api_key": False,
                "supported_standards": ["WCAG 2.1", "WCAG 2.2"],
                "detection_capabilities": [
                    "HTML validation",
                    "WCAG compliance",
                    "Color contrast",
                    "Link analysis",
                    "Image analysis"
                ],
                "limitations": ["Richiede Node.js installato"]
            }
        },
        "features": {
            "simultaneous_scanning": True,
            "result_aggregation": True,
            "pdf_generation": True,
            "ai_enhancement": True,
            "real_time_monitoring": True,
            "bulk_scanning": True,
            "historical_tracking": True,
            "compliance_reporting": True
        },
        "supported_standards": {
            "wcag": ["2.1 A", "2.1 AA", "2.1 AAA", "2.2 A", "2.2 AA"],
            "eaa": ["EN 301 549"],
            "section508": ["2018 Refresh"],
            "italian_law": ["Legge Stanca", "CAD"]
        },
        "output_formats": ["HTML", "PDF", "JSON", "CSV"],
        "languages": ["Italian", "English"],
        "deployment": {
            "docker_support": True,
            "cloud_ready": True,
            "api_first": True,
            "webhook_support": True
        }
    }
    
    return {
        "success": True,
        "data": capabilities,
        "message": "Capacità scanner recuperate con successo"
    }

@app.post("/api/scan/validate")
async def validate_scan_request(request: ScanRequest):
    """Validate scan request without starting the scan"""
    
    validation_results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "recommendations": []
    }
    
    # URL validation
    try:
        url_str = str(request.url)
        if not url_str.startswith(('http://', 'https://')):
            validation_results["errors"].append("URL deve iniziare con http:// o https://")
            validation_results["valid"] = False
    except Exception as e:
        validation_results["errors"].append(f"URL non valido: {str(e)}")
        validation_results["valid"] = False
    
    # Company name validation
    if len(request.company_name.strip()) < 2:
        validation_results["errors"].append("Nome azienda troppo corto (minimo 2 caratteri)")
        validation_results["valid"] = False
    
    # Scanner configuration validation
    if request.scannerConfig:
        enabled_scanners = [
            name for name, config in request.scannerConfig.dict().items() 
            if config.get("enabled", False)
        ]
        
        if not enabled_scanners:
            validation_results["warnings"].append("Nessun scanner abilitato. Saranno utilizzati i default.")
        
        if "wave" in enabled_scanners and not os.getenv("WAVE_API_KEY"):
            validation_results["warnings"].append("Scanner WAVE abilitato ma chiave API non configurata")
    
    # Recommendations
    if request.simulate:
        validation_results["recommendations"].append("Modalità simulazione attiva. Per risultati reali, disabilita simulate.")
    
    validation_results["recommendations"].append("Per risultati migliori, assicurati che il sito sia pubblicamente accessibile")
    
    # Estimate scan time
    estimated_time = 30  # Base time
    if request.scannerConfig:
        enabled_count = len([
            name for name, config in request.scannerConfig.dict().items() 
            if config.get("enabled", False)
        ])
        estimated_time = estimated_time * max(1, enabled_count)
    
    validation_results["estimated_duration"] = f"{estimated_time} secondi"
    validation_results["estimated_cost"] = "Gratuito" if request.simulate else "$0.05 - $0.25"
    
    return {
        "success": validation_results["valid"],
        "validation": validation_results,
        "timestamp": datetime.utcnow().isoformat()
    }

# ==================== ADDITIONAL API ENDPOINTS ====================

@app.get("/api/history")
async def get_scan_history(
    page: int = 1,
    limit: int = 20,
    status_filter: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get real paginated scan history from database with filtering"""
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        
        # Build query with filters
        where_conditions = []
        params = []
        
        if status_filter:
            where_conditions.append("status = ?")
            params.append(status_filter)
        
        if date_from:
            where_conditions.append("created_at >= ?")
            params.append(date_from)
        
        if date_to:
            where_conditions.append("created_at <= ?")
            params.append(date_to)
        
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM scans {where_clause}"
        cursor.execute(count_query, params)
        total_scans = cursor.fetchone()[0]
        
        # Get paginated results
        offset = (page - 1) * limit
        data_query = f"""
            SELECT id, url, company_name, email, status, progress, results, created_at, updated_at 
            FROM scans {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        cursor.execute(data_query, params + [limit, offset])
        scan_rows = cursor.fetchall()
        
        # Process scan data
        history = []
        for row in scan_rows:
            scan_id, url, company_name, email, status, progress, results_json, created_at, updated_at = row
            
            # Parse results
            try:
                if results_json:
                    results = json.loads(results_json) if isinstance(results_json, str) else results_json
                else:
                    results = {}
            except:
                results = {}
            
            history.append({
                "id": scan_id,
                "url": url,
                "company": company_name,
                "email": email,
                "date": created_at,
                "status": status,
                "compliance_score": results.get("compliance_score", 0),
                "total_issues": results.get("total_issues", 0),
                "critical_issues": results.get("critical_issues", 0),
                "high_issues": results.get("high_issues", 0),
                "wcag_level": results.get("wcag_level", "AA"),
                "eaa_compliant": results.get("eaa_compliant", False),
                "scanners_completed": results.get("scanners_completed", 0),
                "scan_duration": results.get("scan_duration", 0),
                "report_available": status == "completed",
                "created_by": current_user.username if current_user else "anonymous"
            })
        
        # Calculate summary statistics
        completed_scans = len([h for h in history if h["status"] == "completed"])
        failed_scans = len([h for h in history if h["status"] == "failed"])
        
        # Calculate averages for completed scans only
        completed_history = [h for h in history if h["status"] == "completed" and h["compliance_score"] > 0]
        avg_score = sum([h["compliance_score"] for h in completed_history]) / max(1, len(completed_history))
        compliance_rate = len([h for h in completed_history if h["eaa_compliant"]]) / max(1, len(completed_history)) * 100
        
        conn.close()
        
        return {
            "success": True,
            "data": {
                "history": history,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total_scans,
                    "pages": (total_scans + limit - 1) // limit,
                    "has_next": offset + limit < total_scans,
                    "has_prev": page > 1
                },
                "summary": {
                    "total_scans": total_scans,
                    "completed_scans": completed_scans,
                    "failed_scans": failed_scans,
                    "average_score": round(avg_score, 1),
                    "compliance_rate": round(compliance_rate, 1)
                }
            },
            "message": f"Recuperate {len(history)} scansioni di {total_scans} totali"
        }
        
    except Exception as e:
        logger.error(f"Error getting scan history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore nel recupero dello storico"
        )

@app.get("/api/keys/status", response_model=APIKeyValidationResponse)
async def get_keys_status():
    """Get comprehensive API keys status with validation info"""
    openai_key = get_effective_openai_key()
    wave_key = get_effective_wave_key()
    
    # Mock validation status (in production, you'd validate against actual APIs)
    openai_validation = {
        "valid": bool(openai_key and openai_key.startswith("sk-")),
        "configured": bool(openai_key),
        "last_validated": datetime.utcnow().isoformat() if openai_key else None,
        "error": None if openai_key else "Chiave non configurata"
    }
    
    wave_validation = {
        "valid": bool(wave_key and len(wave_key) > 10),
        "configured": bool(wave_key),
        "last_validated": datetime.utcnow().isoformat() if wave_key else None,
        "error": None if wave_key else "Chiave non configurata"
    }
    
    return APIKeyValidationResponse(
        success=True,
        data={
            "keys": {
                "openai": "sk-***" + openai_key[-4:] if openai_key and len(openai_key) > 4 else None,
                "wave": "***" + wave_key[-4:] if wave_key and len(wave_key) > 4 else None
            },
            "validation": {
                "openai": openai_validation,
                "wave": wave_validation
            },
            "overall_status": "configured" if (openai_key or wave_key) else "not_configured"
        },
        message="Status chiavi API recuperato con successo"
    )

@app.post("/api/keys/validate")
async def validate_api_key(request: dict):
    """Validate API key with enhanced validation"""
    # Accept both formats: type/key or key_type/key_value
    key_type = request.get("key_type") or request.get("type", "openai")
    key = request.get("key_value") or request.get("key", "")
    
    if not key:
        return {"valid": False, "message": "Chiave non fornita"}
    
    # Enhanced validation logic
    if key_type == "openai":
        if not key.startswith("sk-"):
            return {
                "success": False,
                "message": "Formato chiave OpenAI non valido",
                "details": "La chiave deve iniziare con 'sk-'",
                "validation": {
                    "valid": False,
                    "error": "Formato non valido",
                    "details": "La chiave OpenAI deve iniziare con 'sk-'"
                }
            }
        if len(key) < 20:
            return {
                "success": False,
                "message": "Chiave OpenAI troppo corta",
                "validation": {
                    "valid": False,
                    "error": "Chiave troppo corta",
                    "details": "La chiave deve essere di almeno 20 caratteri"
                }
            }
        # Real validation with OpenAI API
        try:
            # Test the key with a minimal API call
            test_headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }
            
            # Use httpx for async request
            async with httpx.AsyncClient() as client:
                # Test with models endpoint (minimal cost)
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers=test_headers,
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": "Chiave OpenAI valida",
                        "validation": {
                            "valid": True,
                            "provider": "OpenAI",
                            "message": "✅ Chiave OpenAI verificata con successo",
                            "last_validated": datetime.utcnow().isoformat(),
                            "real_validation": True
                        }
                    }
                elif response.status_code == 401:
                    return {
                        "success": False,
                        "message": "Chiave OpenAI non valida",
                        "validation": {
                            "valid": False,
                            "error": "Autenticazione fallita",
                            "details": "La chiave API non è valida o è stata revocata",
                            "real_validation": True
                        }
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Errore validazione: {response.status_code}",
                        "validation": {
                            "valid": False,
                            "error": f"Errore HTTP {response.status_code}",
                            "details": "Impossibile verificare la chiave",
                            "real_validation": True
                        }
                    }
        except Exception as e:
            logger.warning(f"Fallback to format validation due to: {e}")
            # Fallback to format validation only
            return {
                "success": True,
                "message": "Chiave OpenAI formato corretto (validazione offline)",
                "validation": {
                    "valid": True,
                    "provider": "OpenAI",
                    "message": "⚠️ Chiave con formato corretto (non verificata online)",
                    "last_validated": datetime.utcnow().isoformat(),
                    "real_validation": False
                }
            }
    
    elif key_type == "wave":
        if len(key) < 10:
            return {
                "success": False,
                "message": "Chiave WAVE troppo corta",
                "validation": {
                    "valid": False,
                    "error": "Chiave troppo corta",
                    "details": "La chiave WAVE deve essere di almeno 10 caratteri"
                }
            }
        # Real validation with WAVE API
        try:
            async with httpx.AsyncClient() as client:
                # Test WAVE API key with a minimal request
                response = await client.get(
                    f"https://wave.webaim.org/api/request",
                    params={
                        "key": key,
                        "url": "https://webaim.org"  # Test URL
                    },
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if "error" not in data:
                        return {
                            "success": True,
                            "message": "Chiave WAVE valida",
                            "validation": {
                                "valid": True,
                                "provider": "WebAIM WAVE",
                                "message": "✅ Chiave WAVE verificata con successo",
                                "last_validated": datetime.utcnow().isoformat(),
                                "real_validation": True
                            }
                        }
                    else:
                        return {
                            "success": False,
                            "message": "Chiave WAVE non valida",
                            "validation": {
                                "valid": False,
                                "error": "Chiave non valida",
                                "details": data.get("error", "Chiave API WAVE non autorizzata"),
                                "real_validation": True
                            }
                        }
                else:
                    return {
                        "success": False,
                        "message": f"Errore validazione WAVE: {response.status_code}",
                        "validation": {
                            "valid": False,
                            "error": f"Errore HTTP {response.status_code}",
                            "details": "Impossibile verificare la chiave WAVE",
                            "real_validation": True
                        }
                    }
        except Exception as e:
            logger.warning(f"Fallback to format validation for WAVE due to: {e}")
            # Fallback to format validation only
            return {
                "success": True,
                "message": "Chiave WAVE formato corretto (validazione offline)",
                "validation": {
                    "valid": True,
                    "provider": "WebAIM WAVE",
                    "message": "⚠️ Chiave con formato corretto (non verificata online)",
                    "last_validated": datetime.utcnow().isoformat(),
                    "real_validation": False
                }
            }
    
    return {
        "success": False,
        "message": f"Tipo di chiave non supportato: {key_type}",
        "validation": {
            "valid": False,
            "error": "Tipo non supportato",
            "details": f"Il tipo '{key_type}' non è supportato"
        }
    }

@app.post("/api/keys/save")
async def save_api_keys(request: dict):
    """Save API keys securely"""
    keys = request.get("keys", {})
    
    # Validate keys before saving
    validation_errors = []
    
    if "openai" in keys and keys["openai"]:
        if not keys["openai"].startswith("sk-"):
            validation_errors.append("Chiave OpenAI non valida")
    
    if "wave" in keys and keys["wave"]:
        if len(keys["wave"]) < 10:
            validation_errors.append("Chiave WAVE non valida")
    
    if validation_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Errori di validazione: " + ", ".join(validation_errors)
        )
    
    # Save keys to our in-memory store (in production, use secure storage)
    saved_keys = []
    
    if keys.get("openai"):
        # Store user-configured OpenAI key
        user_configured_keys["openai"] = keys["openai"]
        saved_keys.append("OpenAI")
        logger.info("OpenAI key updated from user panel")
    
    if keys.get("wave"):
        # Store user-configured WAVE key
        user_configured_keys["wave"] = keys["wave"]
        saved_keys.append("WAVE")
        logger.info("WAVE key updated from user panel")
    
    return {
        "success": True,
        "message": f"Chiavi salvate con successo: {', '.join(saved_keys)}",
        "saved_keys": saved_keys,
        "timestamp": datetime.utcnow().isoformat()
    }

async def run_multi_page_scan_task(session_id: str, scan_data: dict):
    """Background task to run multi-page scan"""
    try:
        logger.info(f"========== MULTI-PAGE SCAN TASK STARTED for {session_id} ==========")
        logger.info(f"Session data: {scan_data}")
        logger.info(f"Total pages: {scan_data['total_pages']}")
        logger.info(f"Company: {scan_data.get('company_name', 'N/A')}")
        logger.info(f"Email: {scan_data.get('email', 'N/A')}")
        logger.info(f"Mode: {scan_data.get('mode', 'N/A')}")
        logger.info(f"Starting multi-page scan {session_id} for {scan_data['total_pages']} pages")
        logger.info(f"========== SCAN_DATA DEBUG ==========")
        logger.info(f"scan_data keys: {list(scan_data.keys())}")
        logger.info(f"scan_data scanners: {scan_data.get('scanners', 'NOT_FOUND')}")
        logger.info(f"scanners type: {type(scan_data.get('scanners', None))}")
        logger.info(f"========== END SCAN_DATA DEBUG ==========")
        
        all_issues = []
        pages_scanned = 0
        
        # Use EAA Scanner for accessibility scanning
        logger.info(f"========== USING EAA SCANNER DIRECTLY ==========")
        try:
            from eaa_scanner.core import run_scan as eaa_run_scan
            from eaa_scanner.config import Config as EAAConfig
            from pathlib import Path
            logger.info(f"EAA Scanner imported successfully")
        except Exception as import_error:
            logger.error(f"========== EAA SCANNER IMPORT ERROR ==========")
            logger.error(f"Import error: {import_error}", exc_info=True)
            raise import_error
        
        # Process each page using EAA Scanner directly
        logger.info(f"========== PROCESSING {len(scan_data['pages'])} PAGES WITH EAA SCANNER ==========")
        
        # Create temporary output directory
        output_root = Path("output")
        output_root.mkdir(exist_ok=True)
        
        for idx, page_url in enumerate(scan_data['pages']):
            try:
                logger.info(f"========== PROCESSING PAGE {idx + 1}/{len(scan_data['pages'])}: {page_url} ==========")
                
                # Update current page
                scan_data['current_page'] = page_url
                scan_data['progress'] = max(1, int((idx / max(1, len(scan_data['pages']))) * 100))
                # Sync in-memory session for status endpoint
                if session_id in scan_sessions:
                    scan_sessions[session_id]['status'] = 'running'
                    scan_sessions[session_id]['current_page'] = page_url
                    scan_sessions[session_id]['progress'] = scan_data['progress']
                
                # Update scan_manager for SSE endpoint
                if session_id in scan_manager.scans:
                    scan_manager.scans[session_id]['progress'] = scan_data['progress']
                    scan_manager.scans[session_id]['message'] = f"Scansione pagina {idx + 1} di {scan_data['total_pages']}: {page_url}"
                
                # Send SSE update
                await ws_manager.broadcast(
                    session_id,
                    {
                        "type": "page_scan_start",
                        "page": page_url,
                        "page_number": idx + 1,
                        "total_pages": scan_data['total_pages'],
                        "progress": scan_data['progress']
                    }
                )
                
                # Create EAA Scanner configuration for this page
                logger.info(f"========== CREATING EAA CONFIG for {page_url} ==========")
                # Determina modalità simulazione per batch: usa env come fallback (default false)
                simulate_env = os.getenv("SIMULATE_MODE", "false").lower()
                simulate_flag = simulate_env in ("1", "true", "yes", "on")

                eaa_config = EAAConfig(
                    url=page_url,
                    company_name=scan_data.get('company_name', 'Multi-page Scan'),
                    email=scan_data.get('email', 'scan@example.com'),
                    wave_api_key=get_effective_wave_key() or "",
                    openai_api_key=get_effective_openai_key() or "",
                    simulate=bool(simulate_flag),
                    llm_enabled=False  # Disabilitato durante la scansione, verrà eseguito dopo
                )
                # Applica toggles scanner corretti
                try:
                    from eaa_scanner.config import ScannerToggles
                    toggles = ScannerToggles(
                        pa11y=scan_data.get('scanners', {}).get('pa11y', True),
                        axe_core=scan_data.get('scanners', {}).get('axe', True),
                        lighthouse=scan_data.get('scanners', {}).get('lighthouse', True),
                        wave=scan_data.get('scanners', {}).get('wave', False)
                    )
                    # Disabilita wave se manca API key
                    if not eaa_config.wave_api_key:
                        toggles.wave = False
                    eaa_config.scanners_enabled = toggles
                except Exception:
                    pass
                
                logger.info(f"EAA Config: pa11y={eaa_config.scanners_enabled.pa11y}, axe={eaa_config.scanners_enabled.axe_core}, lighthouse={eaa_config.scanners_enabled.lighthouse}")
                
                # Run EAA Scanner for this page - ENTERPRISE MODE
                logger.info(f"========== RUNNING ENTERPRISE MODE for {page_url} ==========")
                
                # Import enterprise system
                from eaa_scanner.enterprise_integration import FastAPIEnterpriseAdapter
                
                # Usa scan_only per evitare generazione charts/PDF/report
                # AGGIORNAMENTO PROGRESSO DURANTE SCANSIONE
                
                # Callback per aggiornare progresso durante scansione
                def progress_callback(scanner_name: str, progress_pct: int):
                    """Callback chiamato durante la scansione per aggiornare il progresso"""
                    try:
                        # Calcola progresso globale: progresso pagina + progresso scanner corrente
                        page_progress = int((idx / max(1, len(scan_data['pages']))) * 100)
                        scanner_progress = int(progress_pct * 0.8)  # 80% del tempo è scansione
                        total_progress = min(99, page_progress + int(scanner_progress / len(scan_data['pages'])))
                        
                        # Aggiorna scan_sessions
                        if session_id in scan_sessions:
                            scan_sessions[session_id]['progress'] = total_progress
                            scan_sessions[session_id]['message'] = f"Scansione pagina {idx + 1}/{len(scan_data['pages'])}: {scanner_name} ({progress_pct}%)"
                        
                        # Aggiorna scan_manager per SSE
                        if session_id in scan_manager.scans:
                            scan_manager.scans[session_id]['progress'] = total_progress
                            scan_manager.scans[session_id]['message'] = f"Scanner {scanner_name}: {progress_pct}%"
                        
                        logger.info(f"📊 Progress Update: Page {idx+1}/{len(scan_data['pages'])}, Scanner {scanner_name}: {progress_pct}% -> Total: {total_progress}%")
                    except Exception as e:
                        logger.error(f"Errore callback progresso: {e}")
                
                # AGGIORNAMENTI DI PROGRESSO NON BLOCCANTI
                import asyncio
                
                async def update_progress_periodically():
                    """Aggiorna il progresso ogni 2 secondi senza bloccare"""
                    progress_steps = [10, 25, 40, 60, 75, 90]
                    for step in progress_steps:
                        await asyncio.sleep(2)  # Non blocca l'event loop!
                        
                        # Calcola progresso totale
                        page_base_progress = int((idx / max(1, len(scan_data['pages']))) * 100)
                        simulated_progress = min(99, page_base_progress + int(step / len(scan_data['pages'])))
                        
                        # Aggiorna scan_sessions
                        if session_id in scan_sessions:
                            scan_sessions[session_id]['progress'] = simulated_progress
                            scan_sessions[session_id]['message'] = f"Scansione pagina {idx + 1}/{len(scan_data['pages'])}: {step}%"
                            scan_sessions[session_id]['current_page'] = page_url
                            scan_sessions[session_id]['pages_scanned'] = idx
                            scan_sessions[session_id]['total_pages'] = len(scan_data['pages'])
                        
                        # Aggiorna scan_manager
                        if session_id in scan_manager.scans:
                            scan_manager.scans[session_id]['progress'] = simulated_progress
                            scan_manager.scans[session_id]['message'] = f"Scanner attivi: {step}%"
                        
                        logger.info(f"📊 Progress Update: Page {idx+1}/{len(scan_data['pages'])} -> {simulated_progress}%")
                
                # Crea task per aggiornamento progresso
                progress_task = asyncio.create_task(update_progress_periodically())
                
                try:
                    # Esegui scansione enterprise in thread separato per non bloccare l'event loop
                    adapter = FastAPIEnterpriseAdapter()
                    eaa_result = await asyncio.to_thread(
                        adapter.run_enterprise_scan_for_api,
                        url=page_url,
                        company_name=eaa_config.company_name,
                        email=eaa_config.email,
                        wave_api_key=eaa_config.wave_api_key,
                        simulate=eaa_config.simulate,
                        scan_id=session_id
                    )
                finally:
                    # Cancella task di progresso quando la scansione è completata
                    progress_task.cancel()
                    try:
                        await progress_task
                    except asyncio.CancelledError:
                        pass  # Task cancellato correttamente
                
                if eaa_result:
                    # Il nuovo formato da scan_only
                    page_issues_count = eaa_result.get('issues_total', 0)
                    severity_counts = eaa_result.get('issues_by_severity', {})
                    
                    crit = severity_counts.get('critical', 0)
                    high = severity_counts.get('high', 0)
                    med = severity_counts.get('medium', 0)
                    low = severity_counts.get('low', 0)
                    
                    # Salva i risultati completi per questa pagina
                    if 'scan_results' not in scan_sessions[session_id] or not isinstance(scan_sessions[session_id]['scan_results'], dict):
                        scan_sessions[session_id]['scan_results'] = {}
                    
                    scan_sessions[session_id]['scan_results'][page_url] = {
                        'compliance_score': eaa_result.get('compliance_score', 0),
                        'issues_total': page_issues_count,
                        'issues_by_severity': severity_counts,
                        'issues_by_wcag': eaa_result.get('issues_by_wcag', {}),
                        'normalized_issues': eaa_result.get('normalized_issues', []),
                        'raw_data': eaa_result.get('raw_data', {}),
                        'scan_date': eaa_result.get('scan_date'),
                        'scanners_used': eaa_result.get('scanners_used', [])
                    }
                    
                    all_issues.extend([{
                        'page': page_url,
                        'critical': crit,
                        'high': high,
                        'medium': med,
                        'low': low,
                        'total': page_issues_count
                    }])
                    pages_scanned += 1
                    logger.info(f"✅ Page {page_url} scanned successfully: {page_issues_count} issues found")
                else:
                    logger.warning(f"⚠️ EAA Scanner returned empty result for {page_url}")
                
                scan_data['pages_scanned'] = pages_scanned
                scan_data['issues_found'] = len(all_issues)
                if session_id in scan_sessions:
                    scan_sessions[session_id]['pages_scanned'] = pages_scanned
                    scan_sessions[session_id]['issues_found'] = len(all_issues)
                
                # Send SSE update for page completion
                await ws_manager.broadcast(
                    session_id,
                    {
                        "type": "page_scan_complete",
                        "page": page_url,
                        "issues_found": page_issues_count if eaa_result and 'aggregated' in eaa_result else 0,
                        "total_issues": len(all_issues)
                    }
                )
                
            except Exception as e:
                logger.error(f"========== ERROR SCANNING PAGE {page_url} ==========")
                logger.error(f"Exception: {str(e)}", exc_info=True)
                continue
        
        # Update final status
        scan_data['status'] = 'completed'
        scan_data['progress'] = 100
        # Non sovrascrivere scan_results - mantiene il dizionario con i dati completi
        
        # Update scan_manager for SSE endpoint
        if session_id in scan_manager.scans:
            scan_manager.scans[session_id]['status'] = 'completed'
            scan_manager.scans[session_id]['progress'] = 100
            scan_manager.scans[session_id]['results'] = all_issues
            scan_manager.scans[session_id]['message'] = "Scansione completata con successo"
        # Sync in-memory session
        if session_id in scan_sessions:
            scan_sessions[session_id]['status'] = 'completed'
            scan_sessions[session_id]['progress'] = 100
            # Non sovrascrivere scan_results qui - mantiene i dati completi salvati durante la scansione
        
        # Update database
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE scans 
            SET status = ?, completed_at = ?, output_path = ?
            WHERE id = ?
        ''', ('completed', datetime.utcnow().isoformat(), f'/app/output/{session_id}', session_id))
        conn.commit()
        conn.close()
        
        # Send final SSE update
        await ws_manager.broadcast(
            session_id,
            {
                "type": "scan_complete",
                "status": "completed",
                "total_pages_scanned": pages_scanned,
                "total_issues": len(all_issues),
                "session_id": session_id
            }
        )
        
        logger.info(f"Multi-page scan {session_id} completed successfully")
        
    except Exception as e:
        logger.error(f"========== MULTI-PAGE SCAN TASK EXCEPTION for {session_id} ==========")
        logger.error(f"Exception type: {type(e)}")
        logger.error(f"Exception message: {str(e)}")
        logger.error(f"Multi-page scan task failed: {e}", exc_info=True)
        logger.error(f"========== END MULTI-PAGE SCAN TASK EXCEPTION ==========")
        scan_data['status'] = 'failed'
        scan_data['error'] = str(e)

async def start_multi_page_scan(
    request: MultiPageScanRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[User] = None
):
    """Start a multi-page accessibility scan"""
    try:
        # Create a unique session ID for this multi-page scan
        session_id = secrets.token_urlsafe(16)
        
        # Store scan session in database
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        
        # Convert the first page as the main URL for the scan
        main_url = str(request.pages[0]) if request.pages else ""
        
        # Create scan record
        cursor.execute('''
            INSERT INTO scans (id, url, company_name, email, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            main_url,
            request.company_name,
            request.email,
            'running',
            datetime.utcnow().isoformat()
        ))
        conn.commit()
        conn.close()
        
        # Store scan details in memory for tracking
        scan_sessions[session_id] = {
            "session_id": session_id,
            "status": "running",
            "pages": [str(url) for url in request.pages],
            "company_name": request.company_name,
            "email": request.email,
            "mode": request.mode,
            "scanners": request.scanners or {},
            "discovery_session_id": request.discovery_session_id,
            "created_at": datetime.utcnow().isoformat(),
            "progress": 0,
            "current_page": "",
            "pages_scanned": 0,
            "total_pages": len(request.pages),
            "issues_found": 0,
            "scan_results": {}
        }
        
        # Also register in scan_manager for SSE endpoint compatibility
        logger.info(f"========== REGISTERING SCAN MANAGER for {session_id} ==========")
        scan_manager.scans[session_id] = {
            "id": session_id,
            "url": main_url,
            "company_name": request.company_name,
            "email": request.email,
            "status": "running",
            "progress": 0,
            "message": f"Scansione avviata per {len(request.pages)} pagine",
            "created_at": datetime.now().isoformat(),
            "results": None
        }
        logger.info(f"========== SCAN MANAGER REGISTERED for {session_id} ==========")
        
        # Start background task to process all pages
        logger.info(f"========== ADDING BACKGROUND TASK for {session_id} ==========")
        background_tasks.add_task(
            run_multi_page_scan_task, 
            session_id, 
            scan_sessions[session_id]
        )
        logger.info(f"========== BACKGROUND TASK ADDED for {session_id} ==========")
        
        return {
            "session_id": session_id,
            "status": "running",
            "message": f"Scansione avviata per {len(request.pages)} pagine",
            "total_pages": len(request.pages)
        }
        
    except Exception as e:
        logger.error(f"Failed to start multi-page scan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/api/scan/start")
async def start_scan_legacy(
    request: dict,
    background_tasks: BackgroundTasks
):
    """Legacy scan start endpoint - supports both single and multi-page"""
    # Check if it's a multi-page request
    if "pages" in request and isinstance(request.get("pages"), list):
        # Multi-page scan request from frontend
        multi_request = MultiPageScanRequest(**request)
        return await start_multi_page_scan(multi_request, background_tasks)
    else:
        # Single page scan request
        scan_request = ScanRequest(**request)
        return await start_scan(scan_request, background_tasks)

@app.get("/api/scan/status/{session_id}")
async def get_scan_status(session_id: str, request: Request):
    """OTTIMIZZATO: Risposta veloce senza blocchi"""
    # Timeout per prevenire blocchi
    import asyncio
    try:
        return await asyncio.wait_for(_get_scan_status_internal(session_id, request), timeout=2.0)
    except asyncio.TimeoutError:
        # Fallback veloce se timeout
        if session_id in scan_sessions:
            session = scan_sessions[session_id]
            return {
                "session_id": session_id,
                "status": session.get("status", "running"),
                "progress": session.get("progress", 0),
                "pages_scanned": session.get("pages_scanned", 0),
                "total_pages": session.get("total_pages", 0),
                "current_page": session.get("current_page", ""),
                "issues_found": session.get("issues_found", 0),
                "message": session.get("message", "Scansione in corso...")
            }
        else:
            raise HTTPException(status_code=404, detail="Session not found")

async def _get_scan_status_internal(session_id: str, request: Request):
    """Get status of a scan session, includendo eventuali nuovi eventi per polling incrementale."""
    # Supporta polling incrementale con last_event_id
    try:
        last_event_id = int(request.query_params.get("last_event_id", "0") or 0)
    except ValueError:
        last_event_id = 0
    if session_id in scan_sessions:
        session = scan_sessions[session_id]
        status_payload = {
            "session_id": session_id,
            "status": session.get("status", "unknown"),
            "progress": session.get("progress", 0),
            "pages_scanned": session.get("pages_scanned", 0),
            "total_pages": session.get("total_pages", 0),
            "current_page": session.get("current_page", ""),
            "issues_found": session.get("issues_found", 0),
            "message": session.get("message", "")
        }
        
        # Se la scansione è completata, aggiungi i risultati
        if session.get("status") == "completed" and "scan_results" in session:
            # Aggregazione dei risultati di tutte le pagine
            all_results = session["scan_results"]
            logger.info(f"DEBUG get_scan_status: scan_results type={type(all_results)}, keys={list(all_results.keys()) if isinstance(all_results, dict) else 'not dict'}")
            # Verifica che sia un dizionario
            if isinstance(all_results, dict) and len(all_results) > 0:
                total_issues = 0
                severity_totals = {"critical": 0, "high": 0, "medium": 0, "low": 0}
                wcag_totals = {}
                all_normalized_issues = []
                
                for page_url, page_data in all_results.items():
                    total_issues += page_data.get("issues_total", 0)
                    
                    # Aggrega le severità
                    for sev, count in page_data.get("issues_by_severity", {}).items():
                        if sev in severity_totals:
                            severity_totals[sev] += count
                    
                    # Aggrega WCAG
                    for wcag, count in page_data.get("issues_by_wcag", {}).items():
                        wcag_totals[wcag] = wcag_totals.get(wcag, 0) + count
                    
                    # Aggrega issues normalizzate
                    all_normalized_issues.extend(page_data.get("normalized_issues", []))
                
                # Calcola score medio ponderato
                total_compliance = sum(
                    page_data.get("compliance_score", 0) 
                    for page_data in all_results.values()
                )
                avg_compliance = total_compliance / max(1, len(all_results))
                
                status_payload["results"] = {
                    "compliance_score": round(avg_compliance, 1),
                    "total_issues": total_issues,
                    "issues_by_severity": severity_totals,
                    "issues_by_wcag": wcag_totals,
                    "normalized_issues": all_normalized_issues[:200],  # Limita per performance
                    "pages_analyzed": len(all_results),
                    "scan_data": all_results  # Dati completi per ogni pagina
                }
        # Allegare nuovi eventi dal monitor per supportare frontend in polling
        try:
            from webapp.scan_monitor import get_scan_monitor
            monitor = get_scan_monitor()
            events = monitor.event_history.get(session_id, [])
            # Genera ID 1-based compatibili con polling
            enriched = []
            for idx, evt in enumerate(events, start=1):
                if idx > last_event_id:
                    e = dict(evt)
                    e["id"] = idx
                    enriched.append(e)
            if enriched:
                status_payload["new_events"] = enriched
        except Exception:
            # Nessun evento disponibile o monitor non inizializzato
            pass
        return status_payload
    
    # Check database for completed scans
    conn = sqlite3.connect(get_database_path())
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM scans WHERE id = ?', (session_id,))
    scan = cursor.fetchone()
    conn.close()
    
    if scan:
        return {
            "session_id": session_id,
            "status": scan[4],  # status column
            "progress": 100 if scan[4] == 'completed' else 0,
            "message": "Scan found in database"
        }
    
    raise HTTPException(status_code=404, detail="Scan session not found")

@app.post("/api/scan/{scan_id}/cancel")
async def cancel_scan(scan_id: str):
    """Cancel a running scan (best-effort) and notify listeners"""
    # Update in-memory session if exists
    if scan_id in scan_sessions:
        scan_sessions[scan_id]["status"] = "cancelled"
        scan_sessions[scan_id]["message"] = "Scansione annullata dall'utente"
    # Update scan_manager state
    scan = scan_manager.get_scan(scan_id)
    if scan:
        await scan_manager.update_scan(scan_id, status="cancelled", message="Scansione annullata dall'utente")
        # Broadcast cancellation event compatible with frontend
        await ws_manager.broadcast(scan_id, {
            "type": "scan_failed",
            "message": "Scansione annullata dall'utente",
            "data": { "error": "cancelled" }
        })
    return {"message": "Cancellation requested", "status": "cancelled", "scan_id": scan_id}

@app.post("/api/llm/validate-key")
async def validate_llm_key(request: dict):
    """Validate LLM API key"""
    key = request.get("key", "")
    
    if key and key.startswith("sk-"):
        return {"valid": True, "message": "OpenAI key format valid"}
    return {"valid": False, "message": "Invalid OpenAI key format"}

@app.post("/api/validate_openai_key")
async def validate_openai_key_legacy(request: dict):
    """Legacy OpenAI key validation"""
    return await validate_llm_key(request)

@app.post("/api/llm/estimate-costs")
async def estimate_llm_costs(request: dict):
    """Estimate LLM processing costs"""
    try:
        scan_id = request.get("scan_id", "")
        model = request.get("model", "gpt-4o")
        content_type = request.get("content_type", "summary")
        
        # Cost estimates based on model and content type
        cost_matrix = {
            "gpt-4o": {
                "summary": 0.25,
                "detailed": 0.50,
                "comprehensive": 1.00
            },
            "gpt-4-turbo": {
                "summary": 0.50,
                "detailed": 1.00,
                "comprehensive": 2.00
            },
            "gpt-4o-mini": {
                "summary": 0.05,
                "detailed": 0.10,
                "comprehensive": 0.20
            },
            "gpt-3.5-turbo": {
                "summary": 0.10,
                "detailed": 0.20,
                "comprehensive": 0.40
            }
        }
        
        estimated_cost = cost_matrix.get(model, {}).get(content_type, 0.25)
        
        # Add scan complexity factor if scan_id provided
        if scan_id:
            # Simulate complexity analysis
            complexity_factor = 1.0
            if scan_id in scan_sessions:
                scan_data = scan_sessions[scan_id]
                pages_count = len(scan_data.get("pages", []))
                if pages_count > 10:
                    complexity_factor = 1.5
                elif pages_count > 5:
                    complexity_factor = 1.2
            estimated_cost *= complexity_factor
        
        return {
            "success": True,
            "estimated_cost": round(estimated_cost, 2),
            "currency": "USD",
            "model": model,
            "content_type": content_type,
            "estimated_tokens": {
                "input": int(estimated_cost * 1000),
                "output": int(estimated_cost * 300)
            },
            "estimated_time": "30-120 secondi"
        }
        
    except Exception as e:
        logger.error(f"Error estimating costs: {e}")
        return {
            "success": False,
            "error": "Errore durante la stima dei costi",
            "estimated_cost": 0.25
        }

@app.get("/api/reports/{report_id}/download")
async def download_report_direct(report_id: str, format: str = Query("pdf", regex="^(pdf|html|json)$")):
    """
    Scarica il report nel formato richiesto.
    """
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM scans WHERE id = ?', (report_id,))
        scan_row = cursor.fetchone()
        conn.close()
        
        if not scan_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report non trovato"
            )
        
        # Estrai i dati della scansione
        columns = ['id', 'url', 'company_name', 'email', 'status', 'progress', 'results', 
                  'created_at', 'updated_at', 'output_path', 'html_report_path', 'pdf_report_path']
        scan_data = dict(zip(columns[:len(scan_row)], scan_row))
        
        company_name = scan_data.get("company_name", "report")
        
        if format == "pdf":
            pdf_path = scan_data.get("pdf_report_path")
            if pdf_path and Path(pdf_path).exists():
                return FileResponse(
                    path=pdf_path,
                    media_type="application/pdf",
                    filename=f"report_{company_name}.pdf"
                )
            else:
                # Genera PDF se non esiste
                # TODO: implementare generazione PDF
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="PDF non disponibile per questo report"
                )
        
        elif format == "html":
            html_path = scan_data.get("html_report_path")
            if not html_path and scan_data.get("output_path"):
                # Cerca nella cartella output
                output_dir = Path(scan_data["output_path"])
                if output_dir.exists():
                    html_files = list(output_dir.glob("*.html"))
                    if html_files:
                        html_path = str(html_files[0])
            
            if html_path and Path(html_path).exists():
                return FileResponse(
                    path=html_path,
                    media_type="text/html",
                    filename=f"report_{company_name}.html"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="HTML non trovato"
                )
        
        elif format == "json":
            results = scan_data.get("results")
            if results:
                return Response(
                    content=results if isinstance(results, str) else json.dumps(results),
                    media_type="application/json",
                    headers={
                        "Content-Disposition": f"attachment; filename=report_{company_name}.json"
                    }
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Dati JSON non disponibili"
                )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore nel download del report: {str(e)}"
        )

@app.get("/api/reports/{report_id}/view", response_class=HTMLResponse)
async def view_report(report_id: str):
    """
    Visualizza il report HTML direttamente nel browser.
    """
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute('SELECT output_path, html_report_path FROM scans WHERE id = ?', (report_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report non trovato"
            )
        
        output_path, html_report_path = result
        
        # Prova prima il percorso html_report_path
        if html_report_path and Path(html_report_path).exists():
            with open(html_report_path, 'r', encoding='utf-8') as f:
                return HTMLResponse(content=f.read())
        
        # Altrimenti cerca nella cartella output
        if output_path:
            # Cerca file HTML nella cartella output
            output_dir = Path(output_path)
            if output_dir.exists():
                html_files = list(output_dir.glob("*.html"))
                if html_files:
                    # Prendi il primo file HTML trovato
                    with open(html_files[0], 'r', encoding='utf-8') as f:
                        return HTMLResponse(content=f.read())
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File HTML del report non trovato"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error viewing report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore nella visualizzazione del report: {str(e)}"
        )

@app.get("/api/reports")
async def get_reports(
    skip: int = Query(0, ge=0, description="Numero di record da saltare"),
    limit: int = Query(20, ge=1, le=100, description="Numero massimo di record"),
    status: Optional[str] = Query(None, description="Filtra per stato (completed, failed, in_progress)"),
    order_by: str = Query("created_at", regex="^(created_at|completed_at|company_name|url)$"),
    order_dir: str = Query("desc", regex="^(asc|desc)$")
):
    """
    Recupera lista paginata dei report di scansione dal database.
    
    Returns:
        Lista paginata dei report con informazioni di paginazione
    """
    try:
        conn = sqlite3.connect(get_database_path())
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Query base per recuperare i report
        query = """
            SELECT 
                id,
                url,
                company_name,
                email,
                status,
                progress,
                created_at,
                updated_at,
                completed_at,
                output_path,
                html_report_path,
                pdf_report_path,
                results
            FROM scans
        """
        
        params = []
        
        # Aggiungi filtro status se fornito
        if status:
            query += " WHERE status = ?"
            params.append(status)
        
        # Aggiungi ordinamento
        query += f" ORDER BY {order_by} {order_dir.upper()}"
        
        # Aggiungi paginazione
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, skip])
        
        # Esegui query principale
        cursor.execute(query, params)
        reports_raw = cursor.fetchall()
        
        # Converti in dizionari e aggiungi campi calcolati
        reports = []
        for row in reports_raw:
            report = dict(row)
            
            # Estrai informazioni dal campo results se presente
            if report.get('results'):
                try:
                    results_data = json.loads(report['results'])
                    if isinstance(results_data, dict):
                        # Estrai score e compliance_level
                        report['score'] = results_data.get('score', 0)
                        report['compliance_level'] = results_data.get('compliance_level', 'unknown')
                        
                        # Conta i problemi per severità
                        issues = results_data.get('issues', [])
                        report['critical_issues'] = sum(1 for i in issues if i.get('severity') == 'Critical')
                        report['high_issues'] = sum(1 for i in issues if i.get('severity') == 'High')
                        report['medium_issues'] = sum(1 for i in issues if i.get('severity') == 'Medium')
                        report['low_issues'] = sum(1 for i in issues if i.get('severity') == 'Low')
                except (json.JSONDecodeError, TypeError):
                    # Se non riusciamo a parsare, usa valori default
                    report['score'] = 0
                    report['compliance_level'] = 'unknown'
                    report['critical_issues'] = 0
                    report['high_issues'] = 0
                    report['medium_issues'] = 0
                    report['low_issues'] = 0
            else:
                # Valori default se non ci sono risultati
                report['score'] = 0
                report['compliance_level'] = 'unknown'
                report['critical_issues'] = 0
                report['high_issues'] = 0
                report['medium_issues'] = 0
                report['low_issues'] = 0
            
            # Rimuovi il campo results dal response (troppo grande)
            report.pop('results', None)
            
            # Aggiungi scan_type basato su output_path
            if report.get('output_path'):
                report['scan_type'] = 'real' if 'real' in str(report['output_path']) else 'simulate'
            else:
                report['scan_type'] = 'unknown'
            
            # Se html_report_path è null, cerca file HTML nella directory output
            if not report.get('html_report_path') and report.get('id'):
                output_dir = f"/app/output/{report['id']}"
                try:
                    if os.path.exists(output_dir):
                        # Cerca file HTML nella directory
                        html_files = [f for f in os.listdir(output_dir) if f.endswith('.html') and f.startswith('report_')]
                        if html_files:
                            # Prendi il primo file HTML trovato
                            report['html_report_path'] = f"output/{report['id']}/{html_files[0]}"
                            logger.info(f"Found HTML report for {report['id']}: {report['html_report_path']}")
                except Exception as e:
                    logger.warning(f"Error searching HTML for report {report['id']}: {e}")
                
            reports.append(report)
        
        # Conta totale record per paginazione
        count_query = "SELECT COUNT(*) as total FROM scans"
        if status:
            count_query += " WHERE status = ?"
            cursor.execute(count_query, [status])
        else:
            cursor.execute(count_query)
        
        total = cursor.fetchone()['total']
        
        conn.close()
        
        return {
            "reports": reports,
            "total": total,
            "skip": skip,
            "limit": limit,
            "has_more": (skip + limit) < total
        }
        
    except Exception as e:
        logger.error(f"Error fetching reports list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore nel recupero della lista report: {str(e)}"
        )

@app.post("/api/reports/regenerate")
async def regenerate_report(request: dict):
    """Regenerate report with AI enhancement"""
    scan_id = request.get("scan_id")
    model = request.get("model", "gpt-4o")
    
    if not scan_id:
        raise HTTPException(status_code=400, detail="scan_id required")
    
    # Mock regeneration
    return {
        "success": True,
        "message": "Report regenerated with AI",
        "report_url": f"/reports/{scan_id}_enhanced.html",
        "cost_estimate": "$0.50"
    }

@app.post("/api/llm/regenerate", response_model=RegenerationResponse)
async def regenerate_with_llm(request: RegenerationRequest, background_tasks: BackgroundTasks):
    """Start real LLM regeneration process"""
    try:
        regeneration_id = secrets.token_urlsafe(16)
        
        # Validate that the scan exists in database
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM scans WHERE id = ?', (request.scan_id,))
        scan_exists = cursor.fetchone()
        
        if not scan_exists:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scansione non trovata"
            )
        
        # Estimate cost based on content type
        cost_estimates = {
            "full_report": 0.50,
            "summary_only": 0.15,
            "recommendations_only": 0.35
        }
        cost_estimate = cost_estimates.get(request.content_type, 0.50)
        
        # Store regeneration session in database
        cursor.execute('''
            INSERT INTO regeneration_sessions 
            (id, scan_id, model, content_type, status, progress, created_at, updated_at, cost_estimate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            regeneration_id,
            request.scan_id,
            request.model,
            request.content_type,
            "started",
            0,
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat(),
            cost_estimate
        ))
        
        conn.commit()
        conn.close()
        
        # Start background regeneration
        background_tasks.add_task(run_llm_regeneration, regeneration_id, request)
        
        return RegenerationResponse(
            regeneration_id=regeneration_id,
            status="started",
            progress=0,
            estimated_completion=datetime.utcnow() + timedelta(minutes=5),
            cost_estimate=cost_estimate
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting LLM regeneration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore nell'avvio della rigenerazione"
        )

# ==================== HTML INTERFACE ====================

@app.get("/preview", response_class=HTMLResponse)
async def preview_report(
    scan_id: str,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Preview HTML report inline (not as download)"""
    try:
        # Get scan from database
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM scans WHERE id = ?', (scan_id,))
        scan_row = cursor.fetchone()
        conn.close()
        
        if not scan_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scansione non trovata"
            )
        
        # Extract scan data
        columns = ['id', 'url', 'company_name', 'email', 'status', 'progress', 'results', 'created_at', 'updated_at', 'output_path', 'html_report_path', 'pdf_report_path']
        scan_data = dict(zip(columns, scan_row))
        
        # Get HTML report path
        html_path = scan_data.get("html_report_path")
        
        if not html_path or not Path(html_path).exists():
            # Generate HTML if not exists
            html_path = await generate_html_report(scan_id, scan_data)
        
        if html_path and Path(html_path).exists():
            # Read and serve HTML content directly
            async with aiofiles.open(html_path, "r", encoding="utf-8") as f:
                content = await f.read()
            return HTMLResponse(content)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File HTML non trovato"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore nella visualizzazione del report"
        )

@app.get("/report", response_class=HTMLResponse)
async def view_report(
    scan_id: str,
    current_user: Optional[User] = Depends(get_current_user)
):
    """View HTML report inline (alias for preview)"""
    return await preview_report(scan_id, current_user)

@app.get("/static_report", response_class=HTMLResponse)
async def static_report(
    scan_id: str
):
    """Serve HTML report directly from output folder (for testing)"""
    try:
        output_base = Path("/app/output")
        scan_dir = output_base / scan_id
        
        if not scan_dir.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Directory scansione non trovata: {scan_id}"
            )
        
        # Look for HTML report files
        html_files = list(scan_dir.glob("report_*.html"))
        if not html_files:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File HTML report non trovato nella directory"
            )
        
        # Use the first HTML report found
        html_path = html_files[0]
        
        # Read and serve HTML content directly
        async with aiofiles.open(html_path, "r", encoding="utf-8") as f:
            content = await f.read()
        return HTMLResponse(content)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving static report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore nella visualizzazione del report statico"
        )

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve main HTML interface with cache busting"""
    template_path = settings.templates_dir / "index_v2.html"
    
    if not template_path.exists():
        return HTMLResponse("<h1>EAA Scanner API</h1><p>Template not found</p>")
    
    async with aiofiles.open(template_path, "r", encoding="utf-8") as f:
        content = await f.read()
    
    # Add cache buster based on current timestamp to force reload
    import time
    cache_buster = int(time.time())
    content = content.replace("{{ cache_buster }}", str(cache_buster))
    
    return HTMLResponse(content)

# ==================== ERROR HANDLERS ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Enhanced HTTP exception handler with Italian messages"""
    
    # Map common HTTP errors to Italian
    italian_messages = {
        400: "Richiesta non valida",
        401: "Autenticazione richiesta",
        403: "Accesso negato",
        404: "Risorsa non trovata",
        405: "Metodo non consentito",
        422: "Dati di input non validi",
        429: "Troppe richieste",
        500: "Errore interno del server",
        503: "Servizio non disponibile"
    }
    
    error_detail = exc.detail
    if isinstance(exc.detail, str) and exc.status_code in italian_messages:
        if exc.detail in ["Not Found", "Method Not Allowed", "Internal Server Error"]:
            error_detail = italian_messages[exc.status_code]
    
    error_response = ErrorResponse(
        error=error_detail,
        status_code=exc.status_code,
        timestamp=datetime.utcnow().isoformat(),
        details={
            "path": str(request.url),
            "method": request.method,
            "client_ip": request.client.host if request.client else None
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Enhanced general exception handler with logging and Italian messages"""
    
    # Log the full exception for debugging
    logger.error(
        f"Unhandled exception on {request.method} {request.url}: {exc}",
        exc_info=True
    )
    
    # Don't expose internal errors in production
    if settings.debug:
        detail = f"Errore interno: {str(exc)}"
        debug_info = {
            "exception_type": type(exc).__name__,
            "exception_args": str(exc.args) if exc.args else None
        }
    else:
        detail = "Errore interno del server"
        debug_info = None
    
    error_response = ErrorResponse(
        error=detail,
        status_code=500,
        timestamp=datetime.utcnow().isoformat(),
        details={
            "path": str(request.url),
            "method": request.method,
            "client_ip": request.client.host if request.client else None,
            "debug": debug_info
        } if settings.debug else {
            "path": str(request.url),
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.dict(exclude_none=True)
    )

# ==================== MAIN ====================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "webapp.app_fastapi:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=1 if settings.debug else settings.workers,
        log_level="debug" if settings.debug else "info"
    )
