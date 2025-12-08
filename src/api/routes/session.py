"""
Jarvis Web Agent - Session Routes
Persistent browser sessions with identity management
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from loguru import logger
import uuid

router = APIRouter()


class SessionCreateRequest(BaseModel):
    """Request to create a new persistent session"""
    name: Optional[str] = Field(None, description="Human-friendly session name")
    identity: Optional[str] = Field(None, description="Fingerprint identity to use")
    proxy_mode: Optional[str] = Field("auto")
    cookies: Optional[List[Dict]] = Field(None, description="Initial cookies to set")
    storage_state: Optional[Dict] = Field(None, description="localStorage/sessionStorage")


class SessionInfo(BaseModel):
    """Session information"""
    session_id: str
    name: Optional[str]
    identity: Optional[str]
    created_at: str
    last_used: Optional[str]
    url: Optional[str]
    active: bool


class SessionCreateResponse(BaseModel):
    """Response after creating a session"""
    success: bool
    session_id: Optional[str] = None
    error: Optional[str] = None


class SessionListResponse(BaseModel):
    """List of active sessions"""
    sessions: List[SessionInfo]


class SessionActionRequest(BaseModel):
    """Execute action in existing session"""
    actions: List[Dict[str, Any]]
    return_screenshot: Optional[bool] = False


class SessionActionResponse(BaseModel):
    """Response from session action"""
    success: bool
    results: List[Dict[str, Any]] = []
    screenshot: Optional[str] = None
    current_url: Optional[str] = None
    error: Optional[str] = None


# In-memory session store (would use Redis in production)
_sessions: Dict[str, Dict] = {}


@router.post("/create", response_model=SessionCreateResponse)
async def create_session(request: Request, session_req: SessionCreateRequest):
    """
    Create a new persistent browser session
    
    Sessions persist browser state including:
    - Cookies and authentication
    - localStorage/sessionStorage
    - Browser fingerprint identity
    
    Useful for:
    - Logged-in browsing (banking, email)
    - Multi-step workflows
    - Maintaining identity across requests
    """
    browser_pool = request.app.state.get_browser_pool()
    
    session_id = str(uuid.uuid4())[:8]
    logger.info(f"Creating session: {session_id}")
    
    try:
        # Create persistent context
        browser = await browser_pool.get_browser()
        
        # Load or create storage state
        context_options = {
            "storage_state": session_req.storage_state
        }
        
        context = await browser.new_context(**context_options)
        
        # Set initial cookies if provided
        if session_req.cookies:
            await context.add_cookies(session_req.cookies)
        
        # Create page
        page = await context.new_page()
        
        # Store session
        _sessions[session_id] = {
            "context": context,
            "page": page,
            "name": session_req.name,
            "identity": session_req.identity,
            "created_at": _get_timestamp(),
            "last_used": None,
            "active": True
        }
        
        return SessionCreateResponse(
            success=True,
            session_id=session_id
        )
        
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        return SessionCreateResponse(
            success=False,
            error=str(e)
        )


@router.get("/list", response_model=SessionListResponse)
async def list_sessions():
    """List all active sessions"""
    sessions = []
    
    for session_id, session in _sessions.items():
        try:
            current_url = session["page"].url if session.get("page") else None
        except:
            current_url = None
            
        sessions.append(SessionInfo(
            session_id=session_id,
            name=session.get("name"),
            identity=session.get("identity"),
            created_at=session.get("created_at", ""),
            last_used=session.get("last_used"),
            url=current_url,
            active=session.get("active", False)
        ))
    
    return SessionListResponse(sessions=sessions)


@router.post("/{session_id}/navigate")
async def navigate_session(session_id: str, url: str):
    """Navigate session to a URL"""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = _sessions[session_id]
    page = session["page"]
    
    try:
        await page.goto(url)
        session["last_used"] = _get_timestamp()
        return {"success": True, "url": page.url}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/{session_id}/action", response_model=SessionActionResponse)
async def session_action(session_id: str, action_req: SessionActionRequest):
    """Execute actions in an existing session"""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = _sessions[session_id]
    page = session["page"]
    
    results = []
    
    try:
        for action in action_req.actions:
            # Import the action executor from browse module
            from src.api.routes.browse import BrowseAction, _execute_action
            
            browse_action = BrowseAction(**action)
            result = await _execute_action(page, browse_action, human_like=True)
            results.append(result.dict())
        
        session["last_used"] = _get_timestamp()
        
        # Screenshot if requested
        screenshot = None
        if action_req.return_screenshot:
            screenshot_bytes = await page.screenshot(type="png")
            import base64
            screenshot = base64.b64encode(screenshot_bytes).decode()
        
        return SessionActionResponse(
            success=True,
            results=results,
            screenshot=screenshot,
            current_url=page.url
        )
        
    except Exception as e:
        logger.error(f"Session action failed: {e}")
        return SessionActionResponse(
            success=False,
            results=results,
            error=str(e)
        )


@router.get("/{session_id}/cookies")
async def get_session_cookies(session_id: str):
    """Get cookies from a session"""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = _sessions[session_id]
    context = session["context"]
    
    cookies = await context.cookies()
    return {"cookies": cookies}


@router.get("/{session_id}/screenshot")
async def get_session_screenshot(session_id: str):
    """Get current screenshot from session"""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = _sessions[session_id]
    page = session["page"]
    
    import base64
    screenshot_bytes = await page.screenshot(type="png")
    screenshot = base64.b64encode(screenshot_bytes).decode()
    
    return {
        "screenshot": screenshot,
        "url": page.url
    }


@router.delete("/{session_id}")
async def close_session(session_id: str):
    """Close and cleanup a session"""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = _sessions[session_id]
    
    try:
        await session["context"].close()
    except:
        pass
    
    del _sessions[session_id]
    logger.info(f"Session closed: {session_id}")
    
    return {"success": True, "session_id": session_id}


@router.post("/{session_id}/save")
async def save_session(session_id: str, path: Optional[str] = None):
    """Save session state to disk for later restoration"""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = _sessions[session_id]
    context = session["context"]
    
    save_path = path or f"sessions/{session_id}.json"
    
    try:
        storage_state = await context.storage_state(path=save_path)
        return {
            "success": True,
            "path": save_path,
            "cookies_count": len(storage_state.get("cookies", []))
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _get_timestamp() -> str:
    """Get current ISO timestamp"""
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"
