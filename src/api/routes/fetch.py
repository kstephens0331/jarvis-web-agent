"""
Jarvis Web Agent - Fetch Routes
Simple page fetching with automatic protection bypass
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, Dict, Any, List
from loguru import logger

from src.browser.pool import BrowserPool
from src.proxy.router import ProxyRouter
from src.stealth.classifier import SiteClassifier

router = APIRouter()


class FetchRequest(BaseModel):
    """Request model for simple fetch operations"""
    url: HttpUrl
    wait_for: Optional[str] = Field(None, description="CSS selector to wait for")
    timeout: Optional[int] = Field(30000, description="Timeout in milliseconds")
    proxy_mode: Optional[str] = Field("auto", description="auto|home|sacvpn|direct")
    extract: Optional[Dict[str, str]] = Field(None, description="CSS selectors to extract")
    screenshot: Optional[bool] = Field(False, description="Capture screenshot")
    headers: Optional[Dict[str, str]] = Field(None, description="Additional headers")


class FetchResponse(BaseModel):
    """Response model for fetch operations"""
    success: bool
    url: str
    status_code: Optional[int] = None
    html: Optional[str] = None
    text: Optional[str] = None
    extracted: Optional[Dict[str, Any]] = None
    screenshot: Optional[str] = None  # Base64 encoded
    proxy_used: Optional[str] = None
    protection_detected: Optional[str] = None
    error: Optional[str] = None


@router.post("", response_model=FetchResponse)
async def fetch_page(request: Request, fetch_req: FetchRequest):
    """
    Fetch a webpage with automatic bot protection handling
    
    Automatically:
    - Selects appropriate proxy based on target site
    - Applies stealth measures
    - Handles Cloudflare and other protections
    - Extracts specified data
    """
    browser_pool: BrowserPool = request.app.state.get_browser_pool()
    
    url = str(fetch_req.url)
    logger.info(f"Fetch request: {url}")
    
    try:
        # Classify site and get recommended approach
        classifier = SiteClassifier()
        site_info = classifier.classify(url)
        
        # Select proxy
        proxy_router = ProxyRouter()
        proxy = proxy_router.select(
            url=url,
            mode=fetch_req.proxy_mode,
            site_classification=site_info
        )
        
        # Get browser from pool
        async with browser_pool.acquire() as browser:
            # Create context with proxy if needed
            context_options = {}
            if proxy:
                context_options["proxy"] = {"server": proxy}
            
            context = await browser.new_context(**context_options)
            page = await context.new_page()
            
            try:
                # Set additional headers
                if fetch_req.headers:
                    await page.set_extra_http_headers(fetch_req.headers)
                
                # Navigate
                response = await page.goto(
                    url,
                    timeout=fetch_req.timeout,
                    wait_until="domcontentloaded"
                )
                
                # Wait for specific element if requested
                if fetch_req.wait_for:
                    await page.wait_for_selector(
                        fetch_req.wait_for,
                        timeout=fetch_req.timeout
                    )
                
                # Check for protection pages
                protection = await _detect_protection(page)
                if protection:
                    logger.warning(f"Protection detected: {protection}")
                    # TODO: Attempt bypass with FlareSolverr
                
                # Get content
                html = await page.content()
                text = await page.inner_text("body")
                
                # Extract specific elements
                extracted = {}
                if fetch_req.extract:
                    for key, selector in fetch_req.extract.items():
                        try:
                            element = await page.query_selector(selector)
                            if element:
                                extracted[key] = await element.inner_text()
                        except Exception as e:
                            extracted[key] = None
                            logger.warning(f"Failed to extract {key}: {e}")
                
                # Screenshot if requested
                screenshot = None
                if fetch_req.screenshot:
                    screenshot_bytes = await page.screenshot(type="png")
                    import base64
                    screenshot = base64.b64encode(screenshot_bytes).decode()
                
                return FetchResponse(
                    success=True,
                    url=url,
                    status_code=response.status if response else None,
                    html=html,
                    text=text,
                    extracted=extracted if extracted else None,
                    screenshot=screenshot,
                    proxy_used=proxy,
                    protection_detected=protection
                )
                
            finally:
                await context.close()
                
    except Exception as e:
        logger.error(f"Fetch failed for {url}: {e}")
        return FetchResponse(
            success=False,
            url=url,
            error=str(e)
        )


async def _detect_protection(page) -> Optional[str]:
    """Detect common bot protection pages"""
    
    # Check page title and content for protection indicators
    title = await page.title()
    title_lower = title.lower() if title else ""
    
    # Cloudflare
    if "just a moment" in title_lower or "checking your browser" in title_lower:
        return "cloudflare"
    
    # Check for Cloudflare challenge
    cf_challenge = await page.query_selector("#challenge-running, #cf-challenge-running")
    if cf_challenge:
        return "cloudflare"
    
    # PerimeterX
    px_block = await page.query_selector("[class*='px-captcha']")
    if px_block:
        return "perimeterx"
    
    # DataDome
    datadome = await page.query_selector("[class*='datadome']")
    if datadome:
        return "datadome"
    
    # hCaptcha
    hcaptcha = await page.query_selector("[class*='h-captcha'], .hcaptcha")
    if hcaptcha:
        return "hcaptcha"
    
    # reCAPTCHA
    recaptcha = await page.query_selector(".g-recaptcha, [class*='recaptcha']")
    if recaptcha:
        return "recaptcha"
    
    return None
