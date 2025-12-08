"""
Jarvis Web Agent - Browse Routes
Complex browser interactions with action sequences
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, Dict, Any, List, Union
from loguru import logger
from enum import Enum

router = APIRouter()


class ActionType(str, Enum):
    CLICK = "click"
    TYPE = "type"
    SELECT = "select"
    WAIT = "wait"
    SCROLL = "scroll"
    SCREENSHOT = "screenshot"
    EXTRACT = "extract"
    EVALUATE = "evaluate"
    WAIT_NAVIGATION = "wait_navigation"
    HOVER = "hover"
    PRESS = "press"


class BrowseAction(BaseModel):
    """Single browser action"""
    action: ActionType
    selector: Optional[str] = None
    value: Optional[str] = None
    timeout: Optional[int] = 5000
    options: Optional[Dict[str, Any]] = None


class BrowseRequest(BaseModel):
    """Request model for browse operations"""
    url: HttpUrl
    actions: List[BrowseAction] = Field(default_factory=list)
    session_id: Optional[str] = Field(None, description="Use existing session")
    proxy_mode: Optional[str] = Field("auto")
    timeout: Optional[int] = Field(30000)
    human_like: Optional[bool] = Field(True, description="Use human-like behavior")


class ActionResult(BaseModel):
    """Result of a single action"""
    action: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None


class BrowseResponse(BaseModel):
    """Response model for browse operations"""
    success: bool
    url: str
    final_url: Optional[str] = None
    action_results: List[ActionResult] = []
    screenshot: Optional[str] = None
    cookies: Optional[List[Dict]] = None
    error: Optional[str] = None


@router.post("", response_model=BrowseResponse)
async def browse_page(request: Request, browse_req: BrowseRequest):
    """
    Execute a sequence of browser actions on a page
    
    Supports:
    - Click, type, select form elements
    - Wait for elements or navigation
    - Extract data
    - Execute JavaScript
    - Human-like behavior simulation
    """
    browser_pool = request.app.state.get_browser_pool()
    
    url = str(browse_req.url)
    logger.info(f"Browse request: {url} with {len(browse_req.actions)} actions")
    
    action_results = []
    
    try:
        async with browser_pool.acquire() as browser:
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                # Navigate to initial URL
                await page.goto(url, timeout=browse_req.timeout)
                
                # Execute actions
                for i, action in enumerate(browse_req.actions):
                    logger.debug(f"Executing action {i+1}: {action.action}")
                    result = await _execute_action(page, action, browse_req.human_like)
                    action_results.append(result)
                    
                    if not result.success:
                        logger.warning(f"Action {i+1} failed: {result.error}")
                        # Continue or break based on action importance
                
                # Get final state
                final_url = page.url
                cookies = await context.cookies()
                
                # Final screenshot
                screenshot_bytes = await page.screenshot(type="png")
                import base64
                screenshot = base64.b64encode(screenshot_bytes).decode()
                
                return BrowseResponse(
                    success=True,
                    url=url,
                    final_url=final_url,
                    action_results=action_results,
                    screenshot=screenshot,
                    cookies=cookies
                )
                
            finally:
                await context.close()
                
    except Exception as e:
        logger.error(f"Browse failed for {url}: {e}")
        return BrowseResponse(
            success=False,
            url=url,
            action_results=action_results,
            error=str(e)
        )


async def _execute_action(page, action: BrowseAction, human_like: bool) -> ActionResult:
    """Execute a single browser action"""
    
    try:
        if action.action == ActionType.CLICK:
            if human_like:
                await _human_click(page, action.selector)
            else:
                await page.click(action.selector, timeout=action.timeout)
            return ActionResult(action="click", success=True)
            
        elif action.action == ActionType.TYPE:
            if human_like:
                await _human_type(page, action.selector, action.value)
            else:
                await page.fill(action.selector, action.value, timeout=action.timeout)
            return ActionResult(action="type", success=True)
            
        elif action.action == ActionType.SELECT:
            await page.select_option(action.selector, action.value, timeout=action.timeout)
            return ActionResult(action="select", success=True)
            
        elif action.action == ActionType.WAIT:
            if action.selector:
                await page.wait_for_selector(action.selector, timeout=action.timeout)
            else:
                await page.wait_for_timeout(action.timeout)
            return ActionResult(action="wait", success=True)
            
        elif action.action == ActionType.WAIT_NAVIGATION:
            await page.wait_for_load_state("networkidle", timeout=action.timeout)
            return ActionResult(action="wait_navigation", success=True)
            
        elif action.action == ActionType.SCROLL:
            direction = action.options.get("direction", "down") if action.options else "down"
            amount = action.options.get("amount", 500) if action.options else 500
            if direction == "down":
                await page.evaluate(f"window.scrollBy(0, {amount})")
            elif direction == "up":
                await page.evaluate(f"window.scrollBy(0, -{amount})")
            elif direction == "bottom":
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            elif direction == "top":
                await page.evaluate("window.scrollTo(0, 0)")
            return ActionResult(action="scroll", success=True)
            
        elif action.action == ActionType.SCREENSHOT:
            screenshot_bytes = await page.screenshot(type="png")
            import base64
            screenshot = base64.b64encode(screenshot_bytes).decode()
            return ActionResult(action="screenshot", success=True, result=screenshot)
            
        elif action.action == ActionType.EXTRACT:
            element = await page.query_selector(action.selector)
            if element:
                text = await element.inner_text()
                return ActionResult(action="extract", success=True, result=text)
            return ActionResult(action="extract", success=False, error="Element not found")
            
        elif action.action == ActionType.EVALUATE:
            result = await page.evaluate(action.value)
            return ActionResult(action="evaluate", success=True, result=result)
            
        elif action.action == ActionType.HOVER:
            await page.hover(action.selector, timeout=action.timeout)
            return ActionResult(action="hover", success=True)
            
        elif action.action == ActionType.PRESS:
            await page.press(action.selector or "body", action.value, timeout=action.timeout)
            return ActionResult(action="press", success=True)
            
        else:
            return ActionResult(
                action=action.action,
                success=False,
                error=f"Unknown action type: {action.action}"
            )
            
    except Exception as e:
        return ActionResult(
            action=action.action,
            success=False,
            error=str(e)
        )


async def _human_click(page, selector: str):
    """Click with human-like behavior"""
    import random
    import asyncio
    
    element = await page.wait_for_selector(selector)
    box = await element.bounding_box()
    
    if box:
        # Add slight randomness to click position
        x = box["x"] + box["width"] / 2 + random.uniform(-5, 5)
        y = box["y"] + box["height"] / 2 + random.uniform(-3, 3)
        
        # Move mouse with slight delay
        await page.mouse.move(x, y, steps=random.randint(10, 25))
        await asyncio.sleep(random.uniform(0.05, 0.15))
        await page.mouse.click(x, y)
    else:
        await page.click(selector)


async def _human_type(page, selector: str, text: str):
    """Type with human-like behavior"""
    import random
    import asyncio
    
    await page.click(selector)
    await asyncio.sleep(random.uniform(0.1, 0.3))
    
    for char in text:
        await page.keyboard.type(char)
        # Variable delay between keystrokes
        delay = random.uniform(0.03, 0.12)
        # Occasional longer pause (thinking)
        if random.random() < 0.05:
            delay += random.uniform(0.2, 0.5)
        await asyncio.sleep(delay)
