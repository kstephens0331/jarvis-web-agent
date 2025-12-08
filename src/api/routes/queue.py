"""
Jarvis Web Agent - Queue Routes
Async job queue for long-running browser tasks
"""

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, Dict, Any, List
from loguru import logger
from enum import Enum
import uuid

router = APIRouter()


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobType(str, Enum):
    FETCH = "fetch"
    BROWSE = "browse"
    SCRAPE = "scrape"
    MONITOR = "monitor"


class JobSubmitRequest(BaseModel):
    """Submit a job to the queue"""
    job_type: JobType
    url: HttpUrl
    actions: Optional[List[Dict]] = None
    extract: Optional[Dict[str, str]] = None
    options: Optional[Dict[str, Any]] = None
    callback_url: Optional[str] = Field(None, description="Webhook to call on completion")
    priority: Optional[int] = Field(5, ge=1, le=10, description="1=highest, 10=lowest")


class JobSubmitResponse(BaseModel):
    """Response after submitting a job"""
    success: bool
    job_id: Optional[str] = None
    position: Optional[int] = None
    error: Optional[str] = None


class JobStatusResponse(BaseModel):
    """Status of a job"""
    job_id: str
    status: JobStatus
    job_type: str
    url: str
    progress: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class QueueStats(BaseModel):
    """Queue statistics"""
    pending: int
    running: int
    completed_24h: int
    failed_24h: int
    avg_duration_seconds: float


# In-memory job store (use Redis in production)
_jobs: Dict[str, Dict] = {}


@router.post("/submit", response_model=JobSubmitResponse)
async def submit_job(
    request: Request,
    job_req: JobSubmitRequest,
    background_tasks: BackgroundTasks
):
    """
    Submit a job to the async queue
    
    Jobs run in the background and can be monitored via /queue/{job_id}
    Optionally provide a callback_url to receive results via webhook
    """
    job_id = str(uuid.uuid4())[:12]
    logger.info(f"Job submitted: {job_id} ({job_req.job_type})")
    
    # Create job record
    job = {
        "job_id": job_id,
        "status": JobStatus.PENDING,
        "job_type": job_req.job_type,
        "url": str(job_req.url),
        "actions": job_req.actions,
        "extract": job_req.extract,
        "options": job_req.options or {},
        "callback_url": job_req.callback_url,
        "priority": job_req.priority,
        "result": None,
        "error": None,
        "created_at": _get_timestamp(),
        "started_at": None,
        "completed_at": None
    }
    
    _jobs[job_id] = job
    
    # Queue the job for background processing
    queue_manager = request.app.state.get_queue_manager()
    browser_pool = request.app.state.get_browser_pool
    
    background_tasks.add_task(
        _process_job,
        job_id,
        job,
        browser_pool
    )
    
    # Calculate queue position
    pending_count = sum(1 for j in _jobs.values() if j["status"] == JobStatus.PENDING)
    
    return JobSubmitResponse(
        success=True,
        job_id=job_id,
        position=pending_count
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get the status of a job"""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = _jobs[job_id]
    
    return JobStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        job_type=job["job_type"],
        url=job["url"],
        result=job["result"],
        error=job["error"],
        created_at=job["created_at"],
        started_at=job["started_at"],
        completed_at=job["completed_at"]
    )


@router.delete("/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a pending job"""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = _jobs[job_id]
    
    if job["status"] == JobStatus.RUNNING:
        return {"success": False, "error": "Cannot cancel running job"}
    
    if job["status"] in [JobStatus.COMPLETED, JobStatus.FAILED]:
        return {"success": False, "error": "Job already finished"}
    
    del _jobs[job_id]
    return {"success": True, "job_id": job_id}


@router.get("/stats", response_model=QueueStats)
async def get_queue_stats():
    """Get queue statistics"""
    from datetime import datetime, timedelta
    
    now = datetime.utcnow()
    day_ago = now - timedelta(hours=24)
    
    pending = sum(1 for j in _jobs.values() if j["status"] == JobStatus.PENDING)
    running = sum(1 for j in _jobs.values() if j["status"] == JobStatus.RUNNING)
    
    # Count completed/failed in last 24h
    completed_24h = 0
    failed_24h = 0
    durations = []
    
    for job in _jobs.values():
        if job["completed_at"]:
            completed_time = datetime.fromisoformat(job["completed_at"].replace("Z", ""))
            if completed_time > day_ago:
                if job["status"] == JobStatus.COMPLETED:
                    completed_24h += 1
                elif job["status"] == JobStatus.FAILED:
                    failed_24h += 1
                
                if job["started_at"]:
                    started = datetime.fromisoformat(job["started_at"].replace("Z", ""))
                    duration = (completed_time - started).total_seconds()
                    durations.append(duration)
    
    avg_duration = sum(durations) / len(durations) if durations else 0
    
    return QueueStats(
        pending=pending,
        running=running,
        completed_24h=completed_24h,
        failed_24h=failed_24h,
        avg_duration_seconds=round(avg_duration, 2)
    )


@router.get("")
async def list_jobs(
    status: Optional[JobStatus] = None,
    limit: int = 20
):
    """List jobs with optional status filter"""
    jobs = list(_jobs.values())
    
    if status:
        jobs = [j for j in jobs if j["status"] == status]
    
    # Sort by created_at descending
    jobs.sort(key=lambda j: j["created_at"], reverse=True)
    
    return {"jobs": jobs[:limit], "total": len(jobs)}


async def _process_job(job_id: str, job: Dict, get_browser_pool):
    """Process a job in the background"""
    logger.info(f"Processing job: {job_id}")
    
    job["status"] = JobStatus.RUNNING
    job["started_at"] = _get_timestamp()
    
    try:
        browser_pool = get_browser_pool()
        
        async with browser_pool.acquire() as browser:
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                # Navigate to URL
                await page.goto(job["url"])
                
                # Execute actions if provided
                if job["actions"]:
                    from src.api.routes.browse import BrowseAction, _execute_action
                    for action in job["actions"]:
                        browse_action = BrowseAction(**action)
                        await _execute_action(page, browse_action, human_like=True)
                
                # Extract data if requested
                result = {}
                if job["extract"]:
                    for key, selector in job["extract"].items():
                        try:
                            element = await page.query_selector(selector)
                            if element:
                                result[key] = await element.inner_text()
                        except:
                            result[key] = None
                
                # Get page content
                result["html"] = await page.content()
                result["url"] = page.url
                
                job["result"] = result
                job["status"] = JobStatus.COMPLETED
                
            finally:
                await context.close()
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        job["status"] = JobStatus.FAILED
        job["error"] = str(e)
    
    job["completed_at"] = _get_timestamp()
    
    # Send callback if configured
    if job.get("callback_url"):
        await _send_callback(job)


async def _send_callback(job: Dict):
    """Send job result to callback URL"""
    import httpx
    
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                job["callback_url"],
                json={
                    "job_id": job["job_id"],
                    "status": job["status"],
                    "result": job["result"],
                    "error": job["error"]
                },
                timeout=10
            )
    except Exception as e:
        logger.error(f"Failed to send callback for job {job['job_id']}: {e}")


def _get_timestamp() -> str:
    """Get current ISO timestamp"""
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"
