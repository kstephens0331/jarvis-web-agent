"""
Jarvis Web Agent - Browser Pool
Manages concurrent Playwright browser instances with stealth
"""

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from typing import Optional, Dict, List, Any
from contextlib import asynccontextmanager
from loguru import logger
import asyncio

from src.stealth.patches import apply_stealth_patches
from src.stealth.fingerprint import FingerprintGenerator


class BrowserPool:
    """
    Manages a pool of browser instances for concurrent operations
    
    Features:
    - Limited concurrent browsers (based on RAM)
    - Automatic stealth patching
    - Context reuse for sessions
    - Health monitoring
    """
    
    def __init__(self, max_browsers: int = 3, headless: bool = True):
        self.max_browsers = max_browsers
        self.headless = headless
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._contexts: Dict[str, BrowserContext] = {}
        self._semaphore = asyncio.Semaphore(max_browsers)
        self._active_count = 0
        self._total_requests = 0
        self._initialized = False
        self._fingerprint_gen = FingerprintGenerator()
    
    async def initialize(self):
        """Initialize the browser pool"""
        if self._initialized:
            return
        
        self._playwright = await async_playwright().start()
        
        # Launch browser with stealth args
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-infobars',
                '--window-position=0,0',
                '--ignore-certificate-errors',
                '--ignore-certificate-errors-spki-list',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu',
                # Stealth args
                '--disable-features=IsolateOrigins,site-per-process',
                '--flag-switches-begin',
                '--flag-switches-end',
            ]
        )
        
        self._initialized = True
        logger.info(f"Browser pool initialized (max: {self.max_browsers}, headless: {self.headless})")
    
    async def close(self):
        """Close all browsers and cleanup"""
        # Close all contexts
        for context in list(self._contexts.values()):
            try:
                await context.close()
            except:
                pass
        self._contexts.clear()
        
        # Close browser
        if self._browser:
            await self._browser.close()
            self._browser = None
        
        # Stop playwright
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        
        self._initialized = False
        logger.info("Browser pool closed")
    
    async def get_browser(self) -> Browser:
        """Get the browser instance"""
        if not self._initialized:
            await self.initialize()
        return self._browser
    
    @asynccontextmanager
    async def acquire(self, identity: Optional[str] = None):
        """
        Acquire a browser context from the pool
        
        Usage:
            async with pool.acquire() as browser:
                context = await browser.new_context()
                page = await context.new_page()
        """
        async with self._semaphore:
            self._active_count += 1
            self._total_requests += 1
            
            try:
                if not self._initialized:
                    await self.initialize()
                
                yield self._browser
                
            finally:
                self._active_count -= 1
    
    async def new_stealth_context(
        self,
        identity: Optional[str] = None,
        proxy: Optional[Dict] = None,
        locale: str = "en-US",
        timezone: str = "America/Chicago"
    ) -> BrowserContext:
        """
        Create a new browser context with stealth measures applied
        
        Args:
            identity: Seed for consistent fingerprinting
            proxy: Proxy configuration
            locale: Browser locale
            timezone: Browser timezone
        """
        if not self._initialized:
            await self.initialize()
        
        # Generate fingerprint
        fingerprint = self._fingerprint_gen.generate(identity)
        
        # Context options
        context_options = {
            "viewport": fingerprint["viewport"],
            "user_agent": fingerprint["user_agent"],
            "locale": locale,
            "timezone_id": timezone,
            "device_scale_factor": fingerprint.get("device_scale_factor", 1),
            "has_touch": fingerprint.get("has_touch", False),
            "is_mobile": fingerprint.get("is_mobile", False),
        }
        
        if proxy:
            context_options["proxy"] = proxy
        
        # Create context
        context = await self._browser.new_context(**context_options)
        
        # Apply stealth patches to all new pages
        context.on("page", lambda page: asyncio.create_task(
            self._apply_page_stealth(page, fingerprint)
        ))
        
        return context
    
    async def _apply_page_stealth(self, page: Page, fingerprint: Dict):
        """Apply stealth patches to a new page"""
        await apply_stealth_patches(page, fingerprint)
    
    def status(self) -> Dict[str, Any]:
        """Get pool status"""
        return {
            "initialized": self._initialized,
            "max_browsers": self.max_browsers,
            "active": self._active_count,
            "available": self.max_browsers - self._active_count,
            "total_requests": self._total_requests,
            "contexts": len(self._contexts)
        }
    
    async def health_check(self) -> bool:
        """Check if the pool is healthy"""
        if not self._initialized:
            return False
        
        try:
            # Try to create and close a context
            context = await self._browser.new_context()
            page = await context.new_page()
            await page.goto("about:blank")
            await context.close()
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
