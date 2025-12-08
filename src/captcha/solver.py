"""
Jarvis Web Agent - CAPTCHA Solver
Self-hosted CAPTCHA solving using Tesseract and Whisper

PROPRIETARY - StephensCode LLC
"""

from typing import Optional, Dict, Any, Tuple
from playwright.async_api import Page
from loguru import logger
import base64
import asyncio


class CaptchaSolver:
    """
    Multi-strategy CAPTCHA solver
    
    Strategies (in order of preference):
    1. Avoidance - human-like behavior to prevent CAPTCHAs
    2. Image CAPTCHA - OCR with Tesseract
    3. Audio CAPTCHA - Speech recognition with Whisper
    4. Escalation - Alert human for manual solving
    """
    
    def __init__(self, whisper_model: str = "base"):
        self.whisper_model = whisper_model
        self._whisper = None
    
    async def solve(self, page: Page) -> bool:
        """
        Attempt to solve any CAPTCHA on the page
        
        Returns True if solved successfully
        """
        captcha_type = await self.detect(page)
        
        if not captcha_type:
            return True  # No CAPTCHA
        
        logger.info(f"CAPTCHA detected: {captcha_type}")
        
        if captcha_type == "recaptcha_v2":
            return await self._solve_recaptcha_v2(page)
        
        elif captcha_type == "recaptcha_v3":
            # v3 is invisible, can't "solve" it - need better behavior
            logger.warning("reCAPTCHA v3 detected - improving human-like behavior")
            return False
        
        elif captcha_type == "hcaptcha":
            return await self._solve_hcaptcha(page)
        
        elif captcha_type == "image":
            return await self._solve_image_captcha(page)
        
        elif captcha_type == "cloudflare":
            # Let FlareSolverr handle this
            logger.info("Cloudflare challenge - use FlareSolverr")
            return False
        
        logger.warning(f"Unknown CAPTCHA type: {captcha_type}")
        return False
    
    async def detect(self, page: Page) -> Optional[str]:
        """Detect CAPTCHA type on page"""
        
        # reCAPTCHA v2 (checkbox)
        recaptcha_v2 = await page.query_selector(
            "iframe[src*='recaptcha'][src*='anchor'], .g-recaptcha"
        )
        if recaptcha_v2:
            return "recaptcha_v2"
        
        # reCAPTCHA v3 (invisible)
        recaptcha_v3 = await page.evaluate("""
            () => typeof grecaptcha !== 'undefined' && 
                  typeof grecaptcha.execute === 'function'
        """)
        if recaptcha_v3:
            return "recaptcha_v3"
        
        # hCaptcha
        hcaptcha = await page.query_selector(
            "iframe[src*='hcaptcha'], .h-captcha"
        )
        if hcaptcha:
            return "hcaptcha"
        
        # Cloudflare challenge
        cf_challenge = await page.query_selector(
            "#challenge-running, #cf-challenge-running, .cf-challenge"
        )
        if cf_challenge:
            return "cloudflare"
        
        # Generic image CAPTCHA
        image_captcha = await page.query_selector(
            "img[alt*='captcha' i], img[src*='captcha' i], .captcha-image"
        )
        if image_captcha:
            return "image"
        
        return None
    
    async def _solve_recaptcha_v2(self, page: Page) -> bool:
        """Solve reCAPTCHA v2 using audio challenge"""
        
        try:
            # Find and click the checkbox
            checkbox_frame = page.frame_locator(
                "iframe[src*='recaptcha'][src*='anchor']"
            )
            checkbox = checkbox_frame.locator("#recaptcha-anchor")
            await checkbox.click()
            
            await asyncio.sleep(2)
            
            # Check if challenge appeared
            challenge_frame = page.frame_locator(
                "iframe[src*='recaptcha'][src*='bframe']"
            )
            
            # Click audio button
            audio_button = challenge_frame.locator("#recaptcha-audio-button")
            if await audio_button.count() > 0:
                await audio_button.click()
                await asyncio.sleep(1)
                
                # Get audio URL
                audio_source = challenge_frame.locator("#audio-source")
                audio_url = await audio_source.get_attribute("src")
                
                if audio_url:
                    # Download and transcribe
                    text = await self._transcribe_audio(audio_url)
                    
                    if text:
                        # Enter transcription
                        input_field = challenge_frame.locator("#audio-response")
                        await input_field.fill(text)
                        
                        # Submit
                        verify_button = challenge_frame.locator("#recaptcha-verify-button")
                        await verify_button.click()
                        
                        await asyncio.sleep(2)
                        
                        # Check if solved
                        solved = await self._check_recaptcha_solved(page)
                        return solved
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to solve reCAPTCHA v2: {e}")
            return False
    
    async def _solve_hcaptcha(self, page: Page) -> bool:
        """Solve hCaptcha - currently limited support"""
        logger.warning("hCaptcha solving not fully implemented")
        
        # hCaptcha is harder - often requires image selection
        # For now, try accessibility mode
        
        try:
            frame = page.frame_locator("iframe[src*='hcaptcha']")
            
            # Try checkbox first
            checkbox = frame.locator("#checkbox")
            if await checkbox.count() > 0:
                await checkbox.click()
                await asyncio.sleep(2)
            
            return False  # Usually needs image challenges
            
        except Exception as e:
            logger.error(f"Failed to solve hCaptcha: {e}")
            return False
    
    async def _solve_image_captcha(self, page: Page) -> bool:
        """Solve simple image CAPTCHA with OCR"""
        
        try:
            import pytesseract
            from PIL import Image
            from io import BytesIO
            
            # Find CAPTCHA image
            captcha_img = await page.query_selector(
                "img[alt*='captcha' i], img[src*='captcha' i], .captcha-image"
            )
            
            if not captcha_img:
                return False
            
            # Screenshot the element
            img_bytes = await captcha_img.screenshot()
            
            # OCR
            image = Image.open(BytesIO(img_bytes))
            text = pytesseract.image_to_string(image, config='--psm 7')
            text = text.strip().replace(" ", "")
            
            if not text:
                return False
            
            logger.info(f"OCR result: {text}")
            
            # Find input field (usually near the image)
            input_field = await page.query_selector(
                "input[name*='captcha' i], input[id*='captcha' i], .captcha-input"
            )
            
            if input_field:
                await input_field.fill(text)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to solve image CAPTCHA: {e}")
            return False
    
    async def _transcribe_audio(self, audio_url: str) -> Optional[str]:
        """Transcribe audio CAPTCHA using Whisper"""
        
        try:
            import httpx
            import tempfile
            import whisper
            
            # Lazy load Whisper model
            if not self._whisper:
                logger.info(f"Loading Whisper model: {self.whisper_model}")
                self._whisper = whisper.load_model(self.whisper_model)
            
            # Download audio
            async with httpx.AsyncClient() as client:
                response = await client.get(audio_url)
                audio_data = response.content
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(audio_data)
                temp_path = f.name
            
            # Transcribe
            result = self._whisper.transcribe(temp_path)
            text = result.get("text", "").strip()
            
            # Clean up
            import os
            os.unlink(temp_path)
            
            logger.info(f"Audio transcription: {text}")
            return text
            
        except Exception as e:
            logger.error(f"Audio transcription failed: {e}")
            return None
    
    async def _check_recaptcha_solved(self, page: Page) -> bool:
        """Check if reCAPTCHA was solved successfully"""
        
        try:
            # Check for success indicator
            checkbox_frame = page.frame_locator(
                "iframe[src*='recaptcha'][src*='anchor']"
            )
            
            # The anchor should have recaptcha-checkbox-checked class
            checked = await checkbox_frame.locator(
                ".recaptcha-checkbox-checked, [aria-checked='true']"
            ).count()
            
            return checked > 0
            
        except:
            return False
