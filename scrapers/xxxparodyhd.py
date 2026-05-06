"""
XXXParodyHD scraper for Stremio
Migrated from Kodi plugin logic
"""

import re
import logging
from typing import List, Optional, Dict
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper, Stream

logger = logging.getLogger(__name__)


class XXXParodyHDScraper(BaseScraper):
    """Scraper for xxxparodyhd.net - Parody adult content"""
    
    SCRAPER_ID = "xxxparodyhd"
    SITE_NAME = "XXXParodyHD"
    SITE_URL = "https://www.xxxparodyhd.net"
    LOGO_URL = "https://www.google.com/s2/favicons?domain=xxxparodyhd.net&sz=128"
    
    def search(self, query: str, year: Optional[str] = None) -> List[Dict]:
        """
        Search for parody movies on XXXParodyHD
        
        Args:
            query: Movie title or keyword
            year: Optional year
        
        Returns:
            List of movie results
        """
        try:
            # Check cache first
            cache_key = f"xxxparodyhd_search_{query}"
            cached = self.cache_get(cache_key)
            if cached:
                return cached
            
            # Build search URL
            search_url = f"{self.SITE_URL}/search/{query.replace(' ', '+')}"
            logger.info(f"Searching XXXParodyHD: {search_url}")
            
            response = self.http_get(search_url)
            if not response:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Find movie items (adjust based on actual layout)
            items = soup.find_all('div', class_=['movie', 'video-item', 'item', 'content-item', 'post'])
            
            for item in items[:15]:
                try:
                    # Extract title
                    title_elem = item.find('a', class_=['title', 'movie-title']) or item.find('h2') or item.find('h3')
                    if not title_elem:
                        title_elem = item.find('a')
                    
                    title = title_elem.text.strip() if title_elem else "Unknown"
                    
                    # Extract URL
                    url = title_elem.get('href', '') if title_elem else ""
                    if not url.startswith('http'):
                        url = self.SITE_URL + url if url.startswith('/') else f"{self.SITE_URL}/{url}"
                    
                    if not url or url == self.SITE_URL:
                        continue
                    
                    # Extract thumbnail
                    thumb_elem = item.find('img')
                    thumbnail = thumb_elem.get('src', '') or thumb_elem.get('data-src', '') if thumb_elem else ""
                    
                    # Extract quality info
                    quality_elem = item.find(string=re.compile(r'\d{3,4}p'))
                    quality = quality_elem if quality_elem else "720p"
                    
                    result = {
                        'title': title,
                        'url': url,
                        'thumbnail': thumbnail,
                        'quality': quality
                    }
                    
                    logger.debug(f"Found: {title} ({quality})")
                    results.append(result)
                    
                except Exception as e:
                    logger.debug(f"Error parsing item: {e}")
                    continue
            
            # Cache results
            self.cache_set(cache_key, results)
            
            return results
            
        except Exception as e:
            logger.error(f"XXXParodyHD search failed: {e}")
            return []
    
    def get_streams(self, video_url: str) -> List[Stream]:
        """
        Extract playable streams from XXXParodyHD movie page
        
        Args:
            video_url: URL of the movie page
        
        Returns:
            List of Stream objects
        """
        try:
            logger.info(f"Getting streams from: {video_url}")
            
            response = self.http_get(video_url)
            if not response:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            streams = []
            
            # Extract movie title
            title_elem = soup.find('h1') or soup.find('title')
            page_title = title_elem.text.strip() if title_elem else "Unknown"
            
            # Extract quality
            quality = self._extract_quality(soup)
            
            # Method 1: Extract from iframes
            iframes = soup.find_all('iframe')
            logger.info(f"Found {len(iframes)} iframes")
            
            for iframe in iframes:
                iframe_src = iframe.get('src', '')
                if iframe_src:
                    if iframe_src.startswith('//'):
                        iframe_src = 'https:' + iframe_src
                    
                    logger.debug(f"Found iframe: {iframe_src[:50]}...")
                    
                    host = self._get_host_from_url(iframe_src)
                    
                    stream = Stream(
                        url=iframe_src,
                        title=page_title,
                        quality=quality,
                        sources=[host],
                        source_url=video_url
                    )
                    streams.append(stream)
            
            # Method 2: Extract direct links from scripts
            script_streams = self._extract_from_scripts(soup, page_title, quality, video_url)
            streams.extend(script_streams)
            
            # Method 3: Look for embedded players
            player_streams = self._extract_from_players(soup, page_title, quality, video_url)
            streams.extend(player_streams)
            
            # Method 4: Extract from links sections
            link_streams = self._extract_from_links(soup, page_title, quality, video_url)
            streams.extend(link_streams)
            
            logger.info(f"Extracted {len(streams)} streams with quality: {quality}")
            
            return streams
            
        except Exception as e:
            logger.error(f"Failed to extract streams: {e}")
            return []
    
    def _extract_quality(self, soup: BeautifulSoup) -> str:
        """
        Extract video quality from page
        
        Args:
            soup: BeautifulSoup object
        
        Returns:
            Quality string (e.g., "720p")
        """
        # Look for quality indicators
        quality_patterns = ['1080p', '720p', '480p', '360p', 'HD', 'SD']
        
        page_text = soup.get_text()
        for quality in quality_patterns:
            if quality in page_text:
                return quality
        
        return "720p"  # Default
    
    def _get_host_from_url(self, url: str) -> str:
        """
        Identify video host from URL
        
        Args:
            url: Video URL
        
        Returns:
            Host name
        """
        hosts_map = {
            'doodstream': 'DoodStream',
            'streamwish': 'StreamWish',
            'vidhidepro': 'VidHidePro',
            'javggvideo': 'JavggVideo',
            'filemoon': 'FileMoon',
            'player4me': 'Player4Me',
        }
        
        url_lower = url.lower()
        for key, value in hosts_map.items():
            if key in url_lower:
                return value
        
        # Extract domain
        match = re.search(r'https?://(?:www\.)?([^./]+)', url)
        return match.group(1) if match else "Unknown"
    
    def _extract_from_scripts(self, soup: BeautifulSoup, title: str, quality: str, source_url: str) -> List[Stream]:
        """
        Extract video sources from JavaScript
        
        Args:
            soup: BeautifulSoup object
            title: Video title
            quality: Video quality
            source_url: Page URL
        
        Returns:
            List of Stream objects
        """
        streams = []
        scripts = soup.find_all('script')
        
        for script in scripts:
            if not script.string:
                continue
            
            script_text = script.string
            
            # Look for iframe URLs in JavaScript
            iframe_urls = re.findall(
                r'https?://[^\s"\']+(?:doodstream|streamwish|vidhidepro|javggvideo)[^\s"\']*',
                script_text,
                re.IGNORECASE
            )
            
            for url in iframe_urls:
                # Clean up URL
                url = re.sub(r'["\'].*$', '', url)
                
                host = self._get_host_from_url(url)
                stream = Stream(
                    url=url,
                    title=title,
                    quality=quality,
                    sources=[host],
                    source_url=source_url
                )
                streams.append(stream)
            
            # Look for direct video files
            video_urls = re.findall(
                r'https?://[^\s"\'<>]+\.(?:mp4|m3u8)',
                script_text,
                re.IGNORECASE
            )
            
            for url in video_urls:
                stream = Stream(
                    url=url,
                    title=title,
                    quality=quality,
                    source_url=source_url
                )
                streams.append(stream)
        
        return streams
    
    def _extract_from_players(self, soup: BeautifulSoup, title: str, quality: str, source_url: str) -> List[Stream]:
        """
        Extract streams from embedded player divs
        
        Args:
            soup: BeautifulSoup object
            title: Video title
            quality: Video quality
            source_url: Page URL
        
        Returns:
            List of Stream objects
        """
        streams = []
        
        # Look for player containers
        player_divs = soup.find_all('div', class_=['player', 'video-player', 'embed-player', 'mediaplayer'])
        
        for player_div in player_divs:
            # Check for data attributes
            for attr in ['data-video', 'data-src', 'data-url', 'data-embed']:
                url = player_div.get(attr, '')
                if url and url.startswith('http'):
                    host = self._get_host_from_url(url)
                    stream = Stream(
                        url=url,
                        title=title,
                        quality=quality,
                        sources=[host],
                        source_url=source_url
                    )
                    streams.append(stream)
        
        return streams
    
    def _extract_from_links(self, soup: BeautifulSoup, title: str, quality: str, source_url: str) -> List[Stream]:
        """
        Extract streams from download/stream links sections
        
        Args:
            soup: BeautifulSoup object
            title: Video title
            quality: Video quality
            source_url: Page URL
        
        Returns:
            List of Stream objects
        """
        streams = []
        
        # Look for link sections
        link_sections = soup.find_all('div', class_=re.compile(r'(link|stream|download)', re.IGNORECASE))
        
        for section in link_sections:
            links = section.find_all('a')
            
            for link in links:
                href = link.get('href', '')
                link_text = link.text.strip()
                
                if href and href.startswith('http'):
                    host = self._get_host_from_url(href)
                    
                    # Use link text as title if available
                    stream_title = link_text if link_text else title
                    
                    stream = Stream(
                        url=href,
                        title=stream_title,
                        quality=quality,
                        sources=[host],
                        source_url=source_url
                    )
                    streams.append(stream)
        
        return streams


# Create singleton instance
xxxparodyhd = XXXParodyHDScraper()


def scrape_xxxparodyhd(query: str, year: Optional[str] = None) -> List[Dict]:
    """
    Function interface for addon.py integration
    
    Args:
        query: Movie search query
        year: Optional year
    
    Returns:
        List of stream dictionaries
    """
    streams = xxxparodyhd.scrape(query, year)
    return [s.to_dict() for s in streams]
