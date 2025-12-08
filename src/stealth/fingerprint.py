"""
Jarvis Web Agent - Fingerprint Generator
Creates consistent, realistic browser fingerprints

PROPRIETARY - StephensCode LLC
"""

from typing import Dict, Any, Optional, List
import hashlib
import random


class FingerprintGenerator:
    """
    Generates browser fingerprints that are:
    - Consistent for the same identity seed
    - Realistic and match real browser populations
    - Unique enough to avoid tracking patterns
    """
    
    # Common screen resolutions (weighted by popularity)
    SCREEN_RESOLUTIONS = [
        (1920, 1080, 0.35),  # Most common
        (1366, 768, 0.20),
        (1536, 864, 0.10),
        (1440, 900, 0.08),
        (1280, 720, 0.07),
        (2560, 1440, 0.06),
        (1680, 1050, 0.05),
        (1600, 900, 0.04),
        (3840, 2160, 0.03),  # 4K
        (2560, 1080, 0.02),  # Ultrawide
    ]
    
    # Chrome versions (recent)
    CHROME_VERSIONS = [
        "120.0.0.0",
        "119.0.0.0",
        "118.0.0.0",
        "121.0.0.0",
    ]
    
    # WebGL renderers (common)
    WEBGL_RENDERERS = [
        ("Intel Inc.", "Intel Iris OpenGL Engine"),
        ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)"),
        ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1060 6GB Direct3D11 vs_5_0 ps_5_0)"),
        ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon RX 580 Series Direct3D11 vs_5_0 ps_5_0)"),
        ("Intel Inc.", "Intel(R) UHD Graphics 620"),
    ]
    
    # Common fonts
    COMMON_FONTS = [
        "Arial", "Verdana", "Times New Roman", "Georgia", "Courier New",
        "Trebuchet MS", "Comic Sans MS", "Impact", "Arial Black",
        "Lucida Console", "Tahoma", "Palatino Linotype", "Segoe UI"
    ]
    
    # Timezone offsets (US common)
    TIMEZONES = [
        "America/New_York",
        "America/Chicago",
        "America/Denver",
        "America/Los_Angeles",
        "America/Phoenix",
    ]
    
    def __init__(self, default_timezone: str = "America/Chicago"):
        self.default_timezone = default_timezone
    
    def generate(self, identity: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a complete browser fingerprint
        
        Args:
            identity: Seed for consistent fingerprinting.
                     Same identity = same fingerprint.
                     None = random fingerprint.
        """
        # Create seeded RNG
        if identity:
            seed = int(hashlib.sha256(identity.encode()).hexdigest()[:8], 16)
            rng = random.Random(seed)
        else:
            rng = random.Random()
        
        # Generate fingerprint components
        screen = self._generate_screen(rng)
        chrome_version = rng.choice(self.CHROME_VERSIONS)
        webgl = rng.choice(self.WEBGL_RENDERERS)
        
        return {
            # Screen
            "viewport": {
                "width": screen["width"],
                "height": screen["height"]
            },
            "screen_width": screen["screen_width"],
            "screen_height": screen["screen_height"],
            "color_depth": screen["color_depth"],
            "device_scale_factor": screen["device_scale_factor"],
            
            # User agent
            "user_agent": self._generate_user_agent(chrome_version, rng),
            "chrome_version": chrome_version,
            
            # Hardware
            "hardware_concurrency": rng.choice([4, 8, 12, 16]),
            "device_memory": rng.choice([4, 8, 16, 32]),
            
            # WebGL
            "webgl_vendor": webgl[0],
            "webgl_renderer": webgl[1],
            
            # Fonts (subset)
            "fonts": self._select_fonts(rng),
            
            # Timezone
            "timezone": self.default_timezone,
            
            # Touch
            "has_touch": rng.random() < 0.1,  # 10% chance
            "is_mobile": False,
            
            # Languages
            "languages": ["en-US", "en"],
            
            # Platform
            "platform": "Win32" if rng.random() > 0.3 else "MacIntel",
            
            # Canvas noise seed
            "canvas_seed": identity or hex(rng.getrandbits(64)),
            
            # Audio context
            "audio_context_noise": rng.uniform(0.0001, 0.001),
        }
    
    def _generate_screen(self, rng: random.Random) -> Dict[str, Any]:
        """Generate screen parameters"""
        # Select resolution based on weights
        weights = [r[2] for r in self.SCREEN_RESOLUTIONS]
        resolutions = [(r[0], r[1]) for r in self.SCREEN_RESOLUTIONS]
        width, height = rng.choices(resolutions, weights=weights)[0]
        
        # Screen is usually same or larger than viewport
        screen_width = width
        screen_height = height
        
        # Viewport accounts for browser chrome
        viewport_height = height - rng.randint(70, 120)  # Browser chrome
        
        # DPR
        dpr = 1.0
        if width >= 2560:  # High res screens often have scaling
            dpr = rng.choice([1.0, 1.25, 1.5, 2.0])
        
        return {
            "width": width,
            "height": viewport_height,
            "screen_width": screen_width,
            "screen_height": screen_height,
            "color_depth": 24,
            "device_scale_factor": dpr
        }
    
    def _generate_user_agent(self, chrome_version: str, rng: random.Random) -> str:
        """Generate a realistic Chrome user agent"""
        
        # Platform-specific parts
        if rng.random() > 0.3:
            # Windows (70%)
            platform = "Windows NT 10.0; Win64; x64"
        else:
            # Mac (30%)
            mac_versions = ["10_15_7", "11_6_0", "12_4_0", "13_1_0", "14_0_0"]
            mac_ver = rng.choice(mac_versions)
            platform = f"Macintosh; Intel Mac OS X {mac_ver}"
        
        major_version = chrome_version.split('.')[0]
        
        return (
            f"Mozilla/5.0 ({platform}) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{chrome_version} Safari/537.36"
        )
    
    def _select_fonts(self, rng: random.Random) -> List[str]:
        """Select a realistic subset of fonts"""
        # Always include core fonts
        fonts = ["Arial", "Times New Roman", "Courier New"]
        
        # Add random others
        additional = rng.sample(
            [f for f in self.COMMON_FONTS if f not in fonts],
            k=rng.randint(5, 10)
        )
        
        return fonts + additional
    
    def generate_family(self, base_identity: str, count: int = 5) -> List[Dict[str, Any]]:
        """
        Generate a family of related fingerprints
        
        Useful for rotating identities while maintaining some consistency
        (e.g., same screen resolution, different other attributes)
        """
        fingerprints = []
        
        for i in range(count):
            identity = f"{base_identity}_{i}"
            fp = self.generate(identity)
            fingerprints.append(fp)
        
        return fingerprints
