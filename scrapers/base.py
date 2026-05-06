"""
Base Scraper Class for Stremio Addon
Provides common functionality for all scrapers
"""

import logging
import time
import hashlib
import json
import random
import threading
import concurrent.futures
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Rotating User Agents untuk avoid blocking
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15',
]


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
    """Simple in-memory cache dengan TTL dan thread safety"""
    
    def __init__(self, ttl_hours: int = 24):
        self.ttl_hours = ttl_hours
        self.cache: Dict[str, tuple] = {}
        self.lock = threading.RLock()  # Thread-safe
    
    def get(self, key: str) -> Optional[Any]:
        """Get from cache jika belum expired"""
        with self.lock:
            if key not in self.cache:
                return None
            
            data, timestamp = self.cache[key]
            
            # Check jika expired
            if datetime.now() - timestamp > timedelta(hours=self.ttl_hours):
                del self.cache[key]
                return None
            
            logger.debug(f"Cache hit: {key}")
            return data
    
    def set(self, key: str, value: Any) -> None:
        """Store in cache"""
        with self.lock:
            self.cache[key] = (value, datetime.now())
            logger.debug(f"Cache set: {key}")
    
    def clear(self) -> None:
        """Clear all cache"""
        with self.lock:
            self.cache.clear()
            logger.info("Cache cleared")
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        with self.lock:
            return {
                "total_keys": len(self.cache),
                "memory_usage_estimate": sum(len(str(v)) for v, _ in self.cache.values())
            }


class BaseScraper:
    """Base class for content scrapers dengan robust error handling"""
    
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
        """Create requests session dengan retry logic"""
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
        
        # Set rotating user agent
        session.headers.update({
            'User-Agent': random.choice(USER_AGENTS)
        })
        
        return session
    
    def http_get(self, url: str, **kwargs) -> Optional[requests.Response]:
        """
        Make HTTP GET request dengan comprehensive error handling
        
        Args:
            url: URL to fetch
            **kwargs: Additional requests arguments
        
        Returns:
            Response object atau None jika failed
        """
        if not url:
            logger.warning("Empty URL provided")
            return None
        
        try:
            timeout = kwargs.pop('timeout', self.REQUEST_TIMEOUT)
            
            logger.debug(f"GET {url[:60]}...")
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
            logger.warning(f"Timeout (>{self.REQUEST_TIMEOUT}s): {url[:60]}")
            return None
        except requests.ConnectionError:
            logger.warning(f"Connection error: {url[:60]}")
            return None
        except requests.HTTPError as e:
            logger.warning(f"HTTP error {e.response.status_code}: {url[:60]}")
            return None
        except Exception as e:
            logger.error(f"Request failed: {str(e)[:100]}")
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
    
    def _make_cache_key(self, *parts: str) -> str:
        """
        Create hash-based cache key (safe untuk special chars)
        
        Args:
            *parts: Key components
        
        Returns:
            Hash-based cache key
        """
        combined = "_".join(str(p) for p in parts)
        hash_val = hashlib.md5(combined.encode()).hexdigest()[:8]
        return f"cache_{hash_val}_{combined[:20]}"
    
    def search(self, query: str, year: Optional[str] = None, timeout: Optional[int] = None) -> List[Dict]:
        """
        Search for content (implement in subclass)
        
        Args:
            query: Search query
            year: Optional year filter
            timeout: Optional timeout in seconds
        
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
        Main scraping method: search dan extract streams
        
        Args:
            query: Search query
            year: Optional year
        
        Returns:
            List of Stream objects
        """
        if not query or not isinstance(query, str):
            logger.error(f"Invalid query type: {type(query)}")
            return []
        
        try:
            logger.info(f"{self.SITE_NAME} scraping: {query[:50]}")
            
            # Search for content dengan timeout
            try:
                results = self.search(query, year, timeout=10)
            except Exception as e:
                logger.error(f"Search failed for {self.SITE_NAME}: {e}")
                return []
            
            if not results:
                logger.warning(f"[{self.SITE_NAME}] No search results for: {query}")
                return []
            
            # Extract streams from first result dengan timeout
            if results:
                first_url = results[0].get('url', '')
                if first_url:
                    try:
                        streams = self.get_streams(first_url)
                        
                        # Filter invalid streams
                        valid_streams = [s for s in streams if s and s.url]
                        logger.info(f"[{self.SITE_NAME}] Got {len(valid_streams)} valid streams")
                        
                        return valid_streams
                    except Exception as e:
                        logger.error(f"get_streams failed for {self.SITE_NAME}: {e}")
                        return []
            
            return []
            
        except Exception as e:
            logger.error(f"Scrape failed: {e}")
            return []
    
    def parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML string"""
        if not html:
            return BeautifulSoup("", 'html.parser')
        return BeautifulSoup(html, 'html.parser')
    
    def extract_urls(self, text: str) -> List[str]:
        """Extract URLs from text"""
        import re
        if not text:
            return []
        
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
    """Registry for all available scrapers dengan async support"""
    
    def __init__(self):
        self.scrapers: Dict[str, BaseScraper] = {}
    
    def register(self, scraper: BaseScraper) -> None:
        """Register a scraper"""
        if not isinstance(scraper, BaseScraper):
            logger.error(f"Invalid scraper type: {type(scraper)}")
            return
        
        self.scrapers[scraper.SCRAPER_ID] = scraper
        logger.info(f"Registered scraper: {scraper.SCRAPER_ID} ({scraper.SITE_NAME})")
    
    def get(self, scraper_id: str) -> Optional[BaseScraper]:
        """Get scraper by ID"""
        return self.scrapers.get(scraper_id)
    
    def get_all(self) -> List[BaseScraper]:
        """Get all scrapers"""
        return list(self.scrapers.values())
    
    def scrape_all(self, query: str) -> Dict[str, List[Stream]]:
        """
        Scrape all sources for a query (SYNCHRONOUS - blocking)
        
        Args:
            query: Search query
        
        Returns:
            Dict dengan scraper_id -> list of streams
        """
        results = {}
        
        for scraper_id, scraper in self.scrapers.items():
            try:
                logger.info(f"Scraping {scraper_id}...")
                streams = scraper.scrape(query)
                
                if streams:
                    results[scraper_id] = streams
                    logger.info(f"Got {len(streams)} streams from {scraper_id}")
                else:
                    logger.debug(f"No streams from {scraper_id}")
                    
            except Exception as e:
                logger.error(f"Error scraping {scraper_id}: {e}")
        
        return results
    
    def scrape_all_async(self, query: str, timeout: int = 20) -> Dict[str, List[Stream]]:
        """
        Scrape all sources ASYNCHRONOUSLY untuk avoid blocking
        
        Args:
            query: Search query
            timeout: Total timeout in seconds
        
        Returns:
            Dict dengan scraper_id -> list of streams
        """
        results = {}
        
        logger.info(f"Starting async scrape for: {query[:50]} (timeout: {timeout}s)")
        
        try:
            # Use ThreadPoolExecutor untuk parallel scraping
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(3, len(self.scrapers))) as executor:
                # Submit all scraping tasks
                future_to_scraper = {
                    executor.submit(scraper.scrape, query): scraper_id
                    for scraper_id, scraper in self.scrapers.items()
                }
                
                # Wait untuk results dengan timeout
                try:
                    for future in concurrent.futures.as_completed(future_to_scraper, timeout=timeout):
                        scraper_id = future_to_scraper[future]
                        
                        try:
                            streams = future.result(timeout=2)  # 2 sec per scraper max
                            
                            if streams:
                                results[scraper_id] = streams
                                logger.info(f"✓ Got {len(streams)} streams from {scraper_id}")
                            else:
                                logger.debug(f"✗ No streams from {scraper_id}")
                                
                        except concurrent.futures.TimeoutError:
                            logger.warning(f"✗ Timeout for {scraper_id}")
                        except Exception as e:
                            logger.error(f"✗ Error from {scraper_id}: {e}")
                
                except concurrent.futures.TimeoutError:
                    logger.warning(f"Global timeout ({timeout}s) reached, using partial results")
                    
                    # Collect any completed results
                    for future in future_to_scraper:
                        if future.done() and not future.cancelled():
                            scraper_id = future_to_scraper[future]
                            try:
                                streams = future.result(timeout=0)
                                if streams:
                                    results[scraper_id] = streams
                            except:
                                pass
        
        except Exception as e:
            logger.error(f"Async scrape failed: {e}")
        
        logger.info(f"Async scrape complete: {len(results)} sources returned results")
        return results


# Global registry
registry = ScraperRegistry()
