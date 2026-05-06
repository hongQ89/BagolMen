"""
Base Scraper Class for Stremio Addon
Provides common functionality for all scrapers
"""

import logging
import time
import hashlib
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class Stream:
    """Stream data object"""
    url: str
    title: str
    quality: str = "unknown"
    sources: List[str] = None
    source_url: str = ""
    
    def __post_init__(self):
        if self.sources is None:
            self.sources = []
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON response"""
        return asdict(self)


class Cache:
    """Simple in-memory cache with TTL"""
    
    def __init__(self, ttl_hours: int = 24):
        self.ttl_hours = ttl_hours
        self.cache: Dict[str, tuple] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get from cache if not expired"""
        if key not in self.cache:
            return None
        
        data, timestamp = self.cache[key]
        
        # Check if expired
        if datetime.now() - timestamp > timedelta(hours=self.ttl_hours):
            del self.cache[key]
            return None
        
        logger.debug(f"Cache hit: {key}")
        return data
    
    def set(self, key: str, value: Any) -> None:
        """Store in cache"""
        self.cache[key] = (value, datetime.now())
        logger.debug(f"Cache set: {key}")
    
    def clear(self) -> None:
        """Clear all cache"""
        self.cache.clear()
        logger.info("Cache cleared")


class BaseScraper:
    """Base class for content scrapers"""
    
    SCRAPER_ID = "base"
    SITE_NAME = "Unknown"
    SITE_URL = ""
    LOGO_URL = ""
    REQUEST_TIMEOUT = 30
    MAX_RETRIES = 3
    
    def __init__(self, ttl_hours: int = 24):
        """Initialize scraper"""
        self.cache = Cache(ttl_hours=ttl_hours)
        self.session = self._create_session()
        logger.info(f"Initialized {self.SITE_NAME} scraper")
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic"""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.MAX_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set headers
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        return session
    
    def http_get(self, url: str, **kwargs) -> Optional[requests.Response]:
        """
        Make HTTP GET request with error handling
        
        Args:
            url: URL to fetch
            **kwargs: Additional requests arguments
        
        Returns:
            Response object or None if failed
        """
        try:
            timeout = kwargs.pop('timeout', self.REQUEST_TIMEOUT)
            
            logger.debug(f"GET {url[:50]}...")
            response = self.session.get(
                url,
                timeout=timeout,
                allow_redirects=True,
                **kwargs
            )
            
            response.raise_for_status()
            logger.debug(f"Response: {response.status_code}")
            
            return response
            
        except requests.Timeout:
            logger.warning(f"Timeout: {url}")
            return None
        except requests.ConnectionError:
            logger.warning(f"Connection error: {url}")
            return None
        except requests.HTTPError as e:
            logger.warning(f"HTTP error {e.response.status_code}: {url}")
            return None
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None
    
    def cache_get(self, key: str) -> Optional[Any]:
        """Get from cache"""
        return self.cache.get(key)
    
    def cache_set(self, key: str, value: Any) -> None:
        """Set cache"""
        self.cache.set(key, value)
    
    def cache_clear(self) -> None:
        """Clear cache"""
        self.cache.clear()
    
    def search(self, query: str, year: Optional[str] = None) -> List[Dict]:
        """
        Search for content (implement in subclass)
        
        Args:
            query: Search query
            year: Optional year filter
        
        Returns:
            List of results
        """
        raise NotImplementedError("Subclass must implement search()")
    
    def get_streams(self, video_url: str) -> List[Stream]:
        """
        Extract streams from video page (implement in subclass)
        
        Args:
            video_url: URL of video page
        
        Returns:
            List of Stream objects
        """
        raise NotImplementedError("Subclass must implement get_streams()")
    
    def scrape(self, query: str, year: Optional[str] = None) -> List[Stream]:
        """
        Main scraping method: search and extract streams
        
        Args:
            query: Search query
            year: Optional year
        
        Returns:
            List of Stream objects
        """
        try:
            logger.info(f"{self.SITE_NAME} scraping: {query}")
            
            # Search for content
            results = self.search(query, year)
            
            if not results:
                logger.info(f"No results found for {query}")
                return []
            
            # Extract streams from first result
            if results:
                first_url = results[0].get('url', '')
                if first_url:
                    streams = self.get_streams(first_url)
                    return streams
            
            return []
            
        except Exception as e:
            logger.error(f"Scrape failed: {e}")
            return []
    
    def parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML string"""
        return BeautifulSoup(html, 'html.parser')
    
    def extract_urls(self, text: str) -> List[str]:
        """Extract URLs from text"""
        import re
        urls = re.findall(
            r'https?://(?:www\.)?[^\s"\'<>]+',
            text
        )
        return list(set(urls))
    
    def get_manifest(self) -> Dict:
        """Get addon manifest for this scraper"""
        return {
            "id": self.SCRAPER_ID,
            "name": self.SITE_NAME,
            "description": f"Streams from {self.SITE_NAME}",
            "version": "1.0.0",
            "author": "Bagol",
            "supportedTypes": ["movie"],
            "formats": ["mp4", "m3u8"],
            "logo": self.LOGO_URL,
            "contentLanguage": ["en"],
            "supportsExternalPlayer": True
        }


class ScraperRegistry:
    """Registry for all available scrapers"""
    
    def __init__(self):
        self.scrapers: Dict[str, BaseScraper] = {}
    
    def register(self, scraper: BaseScraper) -> None:
        """Register a scraper"""
        self.scrapers[scraper.SCRAPER_ID] = scraper
        logger.info(f"Registered scraper: {scraper.SCRAPER_ID}")
    
    def get(self, scraper_id: str) -> Optional[BaseScraper]:
        """Get scraper by ID"""
        return self.scrapers.get(scraper_id)
    
    def get_all(self) -> List[BaseScraper]:
        """Get all scrapers"""
        return list(self.scrapers.values())
    
    def scrape_all(self, query: str) -> Dict[str, List[Stream]]:
        """Scrape all sources for a query"""
        results = {}
        
        for scraper_id, scraper in self.scrapers.items():
            try:
                streams = scraper.scrape(query)
                if streams:
                    results[scraper_id] = streams
                    logger.info(f"Got {len(streams)} streams from {scraper_id}")
            except Exception as e:
                logger.error(f"Error scraping {scraper_id}: {e}")
        
        return results


# Global registry
registry = ScraperRegistry()
