"""
Scan service for managing scan lifecycle
Handles persistence, state management, and coordination
"""

import os
import json
import asyncio
import aiofiles
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
import uuid
import redis.asyncio as aioredis
from ..models.scan import ScanRequest, ScanResult

class ScanService:
    """Service for managing scans with async operations"""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.storage_path = Path(os.getenv("SCAN_STORAGE_PATH", "./output"))
        self.storage_path.mkdir(exist_ok=True, parents=True)
        self._redis_client = None
        
    async def get_redis(self) -> aioredis.Redis:
        """Get or create Redis connection"""
        if not self._redis_client:
            self._redis_client = await aioredis.from_url(
                self.redis_url,
                decode_responses=True
            )
        return self._redis_client
    
    async def create_scan(
        self, 
        request: ScanRequest, 
        user: Optional[Dict] = None
    ) -> str:
        """
        Create a new scan entry
        
        Args:
            request: Scan request details
            user: Optional user context
            
        Returns:
            scan_id: Unique identifier for the scan
        """
        scan_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        scan_data = {
            "id": scan_id,
            "url": str(request.url),
            "company_name": request.company_name,
            "email": request.email,
            "scanners": request.scannerConfig.model_dump(),
            "options": request.options.model_dump(),
            "metadata": request.metadata,
            "status": "pending",
            "progress": 0,
            "created_at": timestamp,
            "updated_at": timestamp,
            "user_id": user.get("id") if user else None,
            "results": None,
            "error": None
        }
        
        # Store in Redis for fast access
        try:
            redis = await self.get_redis()
            await redis.setex(
                f"scan:{scan_id}",
                3600,  # 1 hour expiry
                json.dumps(scan_data)
            )
        except Exception as e:
            print(f"Redis storage failed, using filesystem: {e}")
            # Fallback to filesystem
            await self._save_to_filesystem(scan_id, scan_data)
        
        return scan_id
    
    async def get_scan(self, scan_id: str) -> Optional[Dict]:
        """
        Retrieve scan data by ID
        
        Args:
            scan_id: Unique scan identifier
            
        Returns:
            Scan data dictionary or None if not found
        """
        # Try Redis first
        try:
            redis = await self.get_redis()
            data = await redis.get(f"scan:{scan_id}")
            if data:
                return json.loads(data)
        except Exception as e:
            print(f"Redis retrieval failed: {e}")
        
        # Fallback to filesystem
        return await self._load_from_filesystem(scan_id)
    
    async def update_scan(
        self, 
        scan_id: str, 
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update scan data
        
        Args:
            scan_id: Unique scan identifier
            updates: Dictionary of fields to update
            
        Returns:
            Success status
        """
        scan = await self.get_scan(scan_id)
        if not scan:
            return False
        
        scan.update(updates)
        scan["updated_at"] = datetime.now().isoformat()
        
        # Update in Redis
        try:
            redis = await self.get_redis()
            await redis.setex(
                f"scan:{scan_id}",
                3600,
                json.dumps(scan)
            )
        except Exception as e:
            print(f"Redis update failed: {e}")
            
        # Always update filesystem for persistence
        await self._save_to_filesystem(scan_id, scan)
        return True
    
    async def update_progress(
        self, 
        scan_id: str, 
        progress: int, 
        message: Optional[str] = None,
        current_phase: Optional[str] = None
    ):
        """Update scan progress and status message"""
        updates = {"progress": progress}
        if message:
            updates["message"] = message
        if current_phase:
            updates["current_phase"] = current_phase
            
        await self.update_scan(scan_id, updates)
        
        # Publish to Redis pubsub for real-time updates
        try:
            redis = await self.get_redis()
            await redis.publish(
                f"scan:{scan_id}:updates",
                json.dumps({
                    "type": "progress",
                    "progress": progress,
                    "message": message,
                    "phase": current_phase
                })
            )
        except Exception as e:
            print(f"Redis publish failed: {e}")
    
    async def complete_scan(
        self, 
        scan_id: str, 
        results: Dict[str, Any]
    ):
        """Mark scan as completed with results"""
        await self.update_scan(scan_id, {
            "status": "completed",
            "progress": 100,
            "results": results,
            "completed_at": datetime.now().isoformat()
        })
        
        # Store results separately for larger data
        result_path = self.storage_path / f"eaa_{scan_id}" / "summary.json"
        result_path.parent.mkdir(exist_ok=True, parents=True)
        
        async with aiofiles.open(result_path, 'w') as f:
            await f.write(json.dumps(results, indent=2, ensure_ascii=False))
    
    async def fail_scan(
        self, 
        scan_id: str, 
        error: str
    ):
        """Mark scan as failed with error"""
        await self.update_scan(scan_id, {
            "status": "failed",
            "error": error,
            "failed_at": datetime.now().isoformat()
        })
    
    async def cancel_scan(self, scan_id: str):
        """Cancel a running scan"""
        await self.update_scan(scan_id, {
            "status": "cancelled",
            "cancelled_at": datetime.now().isoformat()
        })
        
        # Publish cancellation event
        try:
            redis = await self.get_redis()
            await redis.publish(
                f"scan:{scan_id}:control",
                json.dumps({"type": "cancel"})
            )
        except Exception as e:
            print(f"Redis cancel publish failed: {e}")
    
    async def reset_scan(self, scan_id: str):
        """Reset scan for retry"""
        await self.update_scan(scan_id, {
            "status": "pending",
            "progress": 0,
            "error": None,
            "results": None,
            "message": "Scan reset for retry"
        })
    
    async def list_scans(
        self,
        status: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
        user_id: Optional[str] = None
    ) -> List[Dict]:
        """
        List scans with optional filtering
        
        Args:
            status: Filter by status
            limit: Maximum results
            offset: Pagination offset
            user_id: Filter by user
            
        Returns:
            List of scan data dictionaries
        """
        scans = []
        
        # Get from Redis if available
        try:
            redis = await self.get_redis()
            keys = await redis.keys("scan:*")
            
            for key in keys:
                if ":updates" in key or ":control" in key:
                    continue
                    
                data = await redis.get(key)
                if data:
                    scan = json.loads(data)
                    
                    # Apply filters
                    if status and scan.get("status") != status:
                        continue
                    if user_id and scan.get("user_id") != user_id:
                        continue
                        
                    scans.append(scan)
        except Exception as e:
            print(f"Redis list failed: {e}")
            
        # Sort by created_at descending
        scans.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        # Apply pagination
        return scans[offset:offset + limit]
    
    async def _save_to_filesystem(self, scan_id: str, data: Dict):
        """Save scan data to filesystem"""
        scan_file = self.storage_path / f"eaa_{scan_id}" / "scan_metadata.json"
        scan_file.parent.mkdir(exist_ok=True, parents=True)
        
        async with aiofiles.open(scan_file, 'w') as f:
            await f.write(json.dumps(data, indent=2, ensure_ascii=False))
    
    async def _load_from_filesystem(self, scan_id: str) -> Optional[Dict]:
        """Load scan data from filesystem"""
        scan_file = self.storage_path / f"eaa_{scan_id}" / "scan_metadata.json"
        
        if not scan_file.exists():
            return None
            
        async with aiofiles.open(scan_file, 'r') as f:
            content = await f.read()
            return json.loads(content)
    
    async def cleanup_old_scans(self, days: int = 7):
        """Remove scans older than specified days"""
        cutoff = datetime.now().timestamp() - (days * 86400)
        
        for scan_dir in self.storage_path.glob("eaa_*"):
            if scan_dir.stat().st_mtime < cutoff:
                # Remove from filesystem
                import shutil
                shutil.rmtree(scan_dir)
                
                # Remove from Redis if present
                scan_id = scan_dir.name.replace("eaa_", "")
                try:
                    redis = await self.get_redis()
                    await redis.delete(f"scan:{scan_id}")
                except Exception:
                    pass
    
    async def close(self):
        """Close connections"""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None