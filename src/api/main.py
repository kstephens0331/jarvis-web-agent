"""
Jarvis Web Agent - API Server
FastAPI application for browser automation and web scraping
"""

from fastapi import FastAPI, HTTPException, Depends, Security, BackgroundTasks
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, Dict, Any
from loguru import logger
import os
import sys

from src.api.routes import fetch, browse, session, queue
from src.browser.pool import BrowserPool
from src.queue.manager import QueueManager
from src.config import settings

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=settings.LOG_LEVEL
)
logger.add(
    "logs/jarvis-web-agent.log",
    rotation="10 MB",
    retention="7 days",
    level="DEBUG"
)

# Initialize FastAPI app
app = FastAPI(
    title="Jarvis Web Agent",
    description="Proprietary web automation module for Project JARVIS",
    version="1.0.0",
    docs_url="/docs" if settings.LOG_LEVEL == "DEBUG" else None,
    redoc_url=None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key security
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    """Verify API key for protected endpoints"""
    if not settings.API_KEY:
        # No API key configured, allow all (dev mode)
        return True
    if api_key != settings.API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return True

# Global instances
browser_pool: Optional[BrowserPool] = None
queue_manager: Optional[QueueManager] = None

@app.on_event("startup")
async def startup():
    """Initialize services on startup"""
    global browser_pool, queue_manager
    
    logger.info("Starting Jarvis Web Agent...")
    
    # Initialize browser pool
    browser_pool = BrowserPool(
        max_browsers=settings.MAX_CONCURRENT_BROWSERS,
        headless=settings.HEADLESS
    )
    await browser_pool.initialize()
    logger.info(f"Browser pool initialized (max: {settings.MAX_CONCURRENT_BROWSERS})")
    
    # Initialize queue manager
    queue_manager = QueueManager(settings.REDIS_URL)
    await queue_manager.connect()
    logger.info("Queue manager connected to Redis")
    
    logger.info("Jarvis Web Agent ready")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    global browser_pool, queue_manager
    
    logger.info("Shutting down Jarvis Web Agent...")
    
    if browser_pool:
        await browser_pool.close()
    if queue_manager:
        await queue_manager.disconnect()
    
    logger.info("Shutdown complete")

# Health check endpoint (no auth required)
@app.get("/health")
async def health_check():
    """Health check endpoint for Docker and monitoring"""
    return {
        "status": "healthy",
        "service": "jarvis-web-agent",
        "browser_pool": browser_pool.status() if browser_pool else "not initialized",
        "queue": queue_manager.status() if queue_manager else "not initialized"
    }

# Include routers with authentication
app.include_router(
    fetch.router,
    prefix="/fetch",
    tags=["fetch"],
    dependencies=[Depends(verify_api_key)]
)

app.include_router(
    browse.router,
    prefix="/browse",
    tags=["browse"],
    dependencies=[Depends(verify_api_key)]
)

app.include_router(
    session.router,
    prefix="/session",
    tags=["session"],
    dependencies=[Depends(verify_api_key)]
)

app.include_router(
    queue.router,
    prefix="/queue",
    tags=["queue"],
    dependencies=[Depends(verify_api_key)]
)

# Dependency injection for routes
def get_browser_pool() -> BrowserPool:
    if not browser_pool:
        raise HTTPException(status_code=503, detail="Browser pool not initialized")
    return browser_pool

def get_queue_manager() -> QueueManager:
    if not queue_manager:
        raise HTTPException(status_code=503, detail="Queue manager not initialized")
    return queue_manager

# Make dependencies available to routes
app.state.get_browser_pool = get_browser_pool
app.state.get_queue_manager = get_queue_manager
