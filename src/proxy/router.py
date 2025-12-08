"""
Jarvis Web Agent - Proxy Router
Intelligent proxy selection based on target site and requirements
"""

from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
from loguru import logger
import random
import asyncio

from src.config import settings
from src.stealth.classifier import SiteClassification, ProtectionLevel


class ProxyRouter:
    """
    Routes requests through optimal proxy based on:
    - Target site protection level
    - Site category (banking, medical, etc.)
    - Explicit mode selection
    - Proxy health status
    """
    
    def __init__(self):
        self._home_proxy = settings.HOME_PROXY_URL if settings.HOME_PROXY_ENABLED else None
        self._sacvpn_nodes = settings.sacvpn_node_list
        self._node_health: Dict[str, bool] = {}
        self._last_used_node: Optional[str] = None
    
    def select(
        self,
        url: str,
        mode: str = "auto",
        site_classification: Optional[SiteClassification] = None
    ) -> Optional[str]:
        """
        Select optimal proxy for a request
        
        Args:
            url: Target URL
            mode: Selection mode
                - "auto": Intelligent selection based on site
                - "home": Force home residential IP
                - "sacvpn": Use SACVPN nodes
                - "direct": No proxy
                - "rotate": Rotate through available proxies
            site_classification: Pre-computed site classification
        
        Returns:
            Proxy URL or None for direct connection
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Explicit mode selection
        if mode == "direct":
            return None
        
        if mode == "home":
            return self._home_proxy
        
        if mode == "sacvpn":
            return self._get_sacvpn_node()
        
        if mode == "rotate":
            return self._rotate_proxy()
        
        # Auto mode - intelligent selection
        if mode == "auto":
            return self._auto_select(domain, site_classification)
        
        logger.warning(f"Unknown proxy mode: {mode}, using direct")
        return None
    
    def _auto_select(
        self,
        domain: str,
        site_classification: Optional[SiteClassification]
    ) -> Optional[str]:
        """Automatically select proxy based on site characteristics"""
        
        # No classification - check basic rules
        if not site_classification:
            # Internal sites - direct
            if self._is_internal(domain):
                return None
            # Default - use home if available
            return self._home_proxy
        
        # Internal sites - always direct
        if site_classification.category.value == "internal":
            return None
        
        # Sites requiring residential IP
        if site_classification.requires_residential:
            if self._home_proxy:
                logger.debug(f"Using home proxy for {domain} (residential required)")
                return self._home_proxy
            else:
                logger.warning(f"Home proxy required for {domain} but not available")
                return None
        
        # High protection - prefer residential
        if site_classification.protection_level in [ProtectionLevel.HIGH, ProtectionLevel.MEDIUM]:
            if self._home_proxy:
                return self._home_proxy
        
        # Low protection - direct is fine
        if site_classification.protection_level == ProtectionLevel.NONE:
            return None
        
        # Default - use home if available, else direct
        return self._home_proxy
    
    def _is_internal(self, domain: str) -> bool:
        """Check if domain is internal"""
        internal = ["stephenscode.dev", "sacvpn.com", "localhost", "127.0.0.1"]
        return any(d in domain for d in internal)
    
    def _get_sacvpn_node(self) -> Optional[str]:
        """Get a healthy SACVPN node"""
        if not self._sacvpn_nodes:
            logger.warning("No SACVPN nodes configured")
            return None
        
        # Filter healthy nodes
        healthy = [
            node for node in self._sacvpn_nodes
            if self._node_health.get(node, True)  # Assume healthy if unknown
        ]
        
        if not healthy:
            logger.warning("No healthy SACVPN nodes available")
            # Try all nodes anyway
            healthy = self._sacvpn_nodes
        
        # Round-robin to avoid using same node twice
        available = [n for n in healthy if n != self._last_used_node]
        if not available:
            available = healthy
        
        node = random.choice(available)
        self._last_used_node = node
        
        return f"socks5://{node}"
    
    def _rotate_proxy(self) -> Optional[str]:
        """Rotate through all available proxies"""
        all_proxies = []
        
        if self._home_proxy:
            all_proxies.append(self._home_proxy)
        
        for node in self._sacvpn_nodes:
            all_proxies.append(f"socks5://{node}")
        
        if not all_proxies:
            return None
        
        return random.choice(all_proxies)
    
    async def health_check(self, proxy: str) -> bool:
        """Check if a proxy is healthy"""
        import httpx
        
        try:
            async with httpx.AsyncClient(
                proxy=proxy,
                timeout=10
            ) as client:
                response = await client.get("https://httpbin.org/ip")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Proxy health check failed for {proxy}: {e}")
            return False
    
    async def refresh_health(self):
        """Refresh health status of all proxies"""
        tasks = []
        
        # Check home proxy
        if self._home_proxy:
            tasks.append(self._check_and_store(self._home_proxy, "home"))
        
        # Check SACVPN nodes
        for node in self._sacvpn_nodes:
            proxy = f"socks5://{node}"
            tasks.append(self._check_and_store(proxy, node))
        
        await asyncio.gather(*tasks)
        
        healthy_count = sum(1 for v in self._node_health.values() if v)
        logger.info(f"Proxy health check complete: {healthy_count}/{len(self._node_health)} healthy")
    
    async def _check_and_store(self, proxy: str, key: str):
        """Check proxy health and store result"""
        healthy = await self.health_check(proxy)
        self._node_health[key] = healthy
    
    def status(self) -> Dict[str, Any]:
        """Get router status"""
        return {
            "home_proxy": self._home_proxy is not None,
            "sacvpn_nodes": len(self._sacvpn_nodes),
            "node_health": dict(self._node_health)
        }
