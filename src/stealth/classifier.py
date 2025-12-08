"""
Jarvis Web Agent - Site Classifier
Classifies websites by protection level and determines optimal approach
"""

from typing import Dict, Any, Optional
from urllib.parse import urlparse
from dataclasses import dataclass
from enum import Enum


class ProtectionLevel(str, Enum):
    NONE = "none"           # No protection, simple fetch works
    LOW = "low"             # Basic protection, stealth browser needed
    MEDIUM = "medium"       # Cloudflare/PerimeterX, need residential IP
    HIGH = "high"           # Heavy protection, may need FlareSolverr
    AUTHENTICATED = "auth"  # Requires login, use sessions


class SiteCategory(str, Enum):
    BANKING = "banking"
    MEDICAL = "medical"
    GOVERNMENT = "government"
    ECOMMERCE = "ecommerce"
    SOCIAL = "social"
    NEWS = "news"
    GENERAL = "general"
    INTERNAL = "internal"   # StephensCode/SACVPN sites


@dataclass
class SiteClassification:
    """Classification result for a site"""
    domain: str
    protection_level: ProtectionLevel
    category: SiteCategory
    requires_residential: bool
    requires_session: bool
    use_flaresolverr: bool
    notes: Optional[str] = None


class SiteClassifier:
    """
    Classifies websites to determine optimal scraping approach
    
    Uses domain-based rules plus learned behavior
    """
    
    # Known protected sites
    HIGH_PROTECTION_DOMAINS = {
        # Cloudflare heavy
        "cloudflare.com",
        "discord.com",
        "medium.com",
        
        # PerimeterX
        "ticketmaster.com",
        "stubhub.com",
        "nike.com",
        
        # DataDome
        "footlocker.com",
        "hermes.com",
        
        # Custom protection
        "linkedin.com",
        "indeed.com",
    }
    
    MEDIUM_PROTECTION_DOMAINS = {
        # Cloudflare standard
        "reddit.com",
        "stackoverflow.com",
        "twitch.tv",
        
        # Rate limited
        "twitter.com",
        "x.com",
        "instagram.com",
        "facebook.com",
    }
    
    BANKING_DOMAINS = {
        "chase.com",
        "bankofamerica.com",
        "wellsfargo.com",
        "citi.com",
        "usbank.com",
        "capitalone.com",
        "discover.com",
        "ally.com",
        "marcus.com",
        "schwab.com",
        "fidelity.com",
        "vanguard.com",
        "etrade.com",
        "robinhood.com",
    }
    
    MEDICAL_DOMAINS = {
        "mychart.com",
        "followmyhealth.com",
        "patientportal",
        "myhealth",
        "portal.epic",
        "athenahealth.com",
        "labcorp.com",
        "questdiagnostics.com",
        "cvs.com",
        "walgreens.com",
    }
    
    GOVERNMENT_DOMAINS = {
        "ssa.gov",
        "irs.gov",
        "healthcare.gov",
        "usa.gov",
        "dmv.gov",
        "txdmv.gov",
        "texas.gov",
        "uscis.gov",
        "state.gov",
    }
    
    INTERNAL_DOMAINS = {
        "stephenscode.dev",
        "sacvpn.com",
        "localhost",
        "127.0.0.1",
    }
    
    def __init__(self):
        self._cache: Dict[str, SiteClassification] = {}
    
    def classify(self, url: str) -> SiteClassification:
        """
        Classify a URL and return recommended approach
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Remove www prefix
        if domain.startswith("www."):
            domain = domain[4:]
        
        # Check cache
        if domain in self._cache:
            return self._cache[domain]
        
        # Classify
        classification = self._classify_domain(domain)
        self._cache[domain] = classification
        
        return classification
    
    def _classify_domain(self, domain: str) -> SiteClassification:
        """Classify a domain"""
        
        # Check internal sites first
        if self._matches_any(domain, self.INTERNAL_DOMAINS):
            return SiteClassification(
                domain=domain,
                protection_level=ProtectionLevel.NONE,
                category=SiteCategory.INTERNAL,
                requires_residential=False,
                requires_session=False,
                use_flaresolverr=False,
                notes="Internal site - direct access"
            )
        
        # Banking
        if self._matches_any(domain, self.BANKING_DOMAINS):
            return SiteClassification(
                domain=domain,
                protection_level=ProtectionLevel.AUTHENTICATED,
                category=SiteCategory.BANKING,
                requires_residential=True,
                requires_session=True,
                use_flaresolverr=False,
                notes="Banking - use home IP, maintain session"
            )
        
        # Medical
        if self._matches_any(domain, self.MEDICAL_DOMAINS):
            return SiteClassification(
                domain=domain,
                protection_level=ProtectionLevel.AUTHENTICATED,
                category=SiteCategory.MEDICAL,
                requires_residential=True,
                requires_session=True,
                use_flaresolverr=False,
                notes="Medical - use home IP, maintain session"
            )
        
        # Government
        if self._matches_any(domain, self.GOVERNMENT_DOMAINS):
            return SiteClassification(
                domain=domain,
                protection_level=ProtectionLevel.MEDIUM,
                category=SiteCategory.GOVERNMENT,
                requires_residential=True,
                requires_session=True,
                use_flaresolverr=False,
                notes="Government - use home IP"
            )
        
        # High protection
        if self._matches_any(domain, self.HIGH_PROTECTION_DOMAINS):
            return SiteClassification(
                domain=domain,
                protection_level=ProtectionLevel.HIGH,
                category=SiteCategory.GENERAL,
                requires_residential=True,
                requires_session=False,
                use_flaresolverr=True,
                notes="Heavy protection - may need FlareSolverr"
            )
        
        # Medium protection
        if self._matches_any(domain, self.MEDIUM_PROTECTION_DOMAINS):
            return SiteClassification(
                domain=domain,
                protection_level=ProtectionLevel.MEDIUM,
                category=SiteCategory.SOCIAL,
                requires_residential=True,
                requires_session=False,
                use_flaresolverr=False,
                notes="Standard Cloudflare - residential IP recommended"
            )
        
        # Default - low/no protection
        return SiteClassification(
            domain=domain,
            protection_level=ProtectionLevel.LOW,
            category=SiteCategory.GENERAL,
            requires_residential=False,
            requires_session=False,
            use_flaresolverr=False,
            notes="Standard site - stealth browser sufficient"
        )
    
    def _matches_any(self, domain: str, domain_set: set) -> bool:
        """Check if domain matches any in set (including subdomains)"""
        for d in domain_set:
            if domain == d or domain.endswith("." + d):
                return True
            if d in domain:  # Partial match for things like "myhealth"
                return True
        return False
    
    def add_classification(
        self,
        domain: str,
        protection_level: ProtectionLevel,
        category: SiteCategory,
        **kwargs
    ):
        """Manually add or override a classification"""
        self._cache[domain] = SiteClassification(
            domain=domain,
            protection_level=protection_level,
            category=category,
            requires_residential=kwargs.get("requires_residential", False),
            requires_session=kwargs.get("requires_session", False),
            use_flaresolverr=kwargs.get("use_flaresolverr", False),
            notes=kwargs.get("notes")
        )
