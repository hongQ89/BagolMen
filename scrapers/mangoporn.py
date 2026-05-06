"""
MangoPorn scraper for Stremio
Migrated from Kodi plugin logic
"""

import re
import logging
from typing import List, Optional, Dict
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper, Stream

logger = logging.getLogger(__name__)


class MangoPornScraper(BaseScraper):
    """Scraper for mangoporn.net - General adult content"""
    
    SCRAPER_ID = "mangoporn"
    SITE_NAME = "MangoPorn"
    SITE_URL = "https://www.mangoporn.net"
    LOGO_URL = "https://www.google.com/s2/favicons?domain=mangoporn.net&sz=128"
    
    def search(self, query: str, year: Optional[str] = None) -> List[Dict]:
        """
        Search for movies on MangoPorn
        
        Args:
            query: Movie title or keyword
            year: Optional year
        
        Returns:
            List of movie results
        """
        try:
            # Check cache first
            cache_key = f"mangoporn_search_{query}"
            cached = self.cache_get(cache_key)
            if cached:
                return cached
            
            # Build search URL - try multiple patterns
            search_patterns = [
                f"{self.SITE_URL}/search?q={query.replace(' ', '+')}",
                f"{self.SITE_URL}/search/{query.replace(' ', '-')}",
                f"{self.SITE_URL}/?s={query.replace(' ', '+')}",
            ]
            
            results = []
            
            for search_url in search_patterns:
                logger.info(f"Searching MangoPorn: {search_url}")
                
                response = self.http_get(search_url)
                if not response:
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find movie items (adjust based on actual layout)
                items = soup.find_all('div', class_=['movie', 'video-item', 'item', 'content-item', 'post', 'entry'])
                
                if not items:
                    continue
                
                for item in items[:20]:
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
                        
                        # Extract duration
                        duration_elem = item.find(string=re.compile(r'\d+:\d+'))
                        duration = duration_elem if duration_elem else ""
                        
                        result = {
                            'title': title,
                            'url': url,
                            'thumbnail': thumbnail,
                            'duration': duration
                        }
                        
                        logger.debug(f"Found: {title}")
                        results.append(result)
                        
                    except Exception as e:
                        logger.debug(f"Error parsing item: {e}")
                        continue
                
                # If we found results, no need to try other patterns
                if results:
                    break
            
            # Cache results
            self.cache_set(cache_key, results)
            
            return results
            
        except Exception as e:
            logger.error(f"MangoPorn search failed: {e}")
            return []
    
    def get_streams(self, video_url: str) -> List[Stream]:
        """
        Extract playable streams from MangoPorn movie page
        
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
                        sources=[host],
                        source_url=video_url
                    )
                    streams.append(stream)
            
            # Method 2: Extract direct links from scripts
            script_streams = self._extract_from_scripts(soup, page_title, video_url)
            streams.extend(script_streams)
            
            # Method 3: Look for embedded players
            player_streams = self._extract_from_players(soup, page_title, video_url)
            streams.extend(player_streams)
            
            # Method 4: Extract from buttons/links
            link_streams = self._extract_from_links(soup, page_title, video_url)
            streams.extend(link_streams)
            
            # Method 5: Extract from video element sources
            video_streams = self._extract_from_video_tags(soup, page_title, video_url)
            streams.extend(video_streams)
            
            logger.info(f"Extracted {len(streams)} streams")
            
            return streams
            
        except Exception as e:
            logger.error(f"Failed to extract streams: {e}")
            return []
    
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
            'filemoon': 'FileMoon',
            'lulustream': 'LuluStream',
            'vidguard': 'Vidguard',
            'player4me': 'Player4Me',
            'vidnest': 'VidNest',
        }
        
        url_lower = url.lower()
        for key, value in hosts_map.items():
            if key in url_lower:
                return value
        
        # Extract domain
        match = re.search(r'https?://(?:www\.)?([^./]+)', url)
        return match.group(1) if match else "Unknown"
    
    def _extract_from_scripts(self, soup: BeautifulSoup, title: str, source_url: str) -> List[Stream]:
        """
        Extract video sources from JavaScript
        
        Args:
            soup: BeautifulSoup object
            title: Video title
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
                r'https?://[^\s"\']+(?:doodstream|filemoon|lulustream|vidguard|player4me|vidnest)[^\s"\']*',
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
                    source_url=source_url
                )
                streams.append(stream)
        
        return streams
    
    def _extract_from_players(self, soup: BeautifulSoup, title: str, source_url: str) -> List[Stream]:
        """
        Extract streams from embedded player divs
        
        Args:
            soup: BeautifulSoup object
            title: Video title
            source_url: Page URL
        
        Returns:
            List of Stream objects
        """
        streams = []
        
        # Look for player containers
        player_divs = soup.find_all('div', class_=['player', 'video-player', 'embed-player', 'mediaplayer', 'jwplayer'])
        
        for player_div in player_divs:
            # Check for data attributes
            for attr in ['data-video', 'data-src', 'data-url', 'data-embed', 'data-file']:
                url = player_div.get(attr, '')
                if url and url.startswith('http'):
                    host = self._get_host_from_url(url)
                    stream = Stream(
                        url=url,
                        title=title,
                        sources=[host],
                        source_url=source_url
                    )
                    streams.append(stream)
        
        return streams
    
    def _extract_from_links(self, soup: BeautifulSoup, title: str, source_url: str) -> List[Stream]:
        """
        Extract streams from download/stream buttons and links
        
        Args:
            soup: BeautifulSoup object
            title: Video title
            source_url: Page URL
        
        Returns:
            List of Stream objects
        """
        streams = []
        
        # Look for link buttons
        buttons = soup.find_all('a', class_=re.compile(r'(download|stream|play|link|button)', re.IGNORECASE))
        
        for button in buttons:
            href = button.get('href', '')
            btn_text = button.text.strip()
            
            if href and href.startswith('http'):
                host = self._get_host_from_url(href)
                
                stream_title = btn_text if btn_text else title
                
                stream = Stream(
                    url=href,
                    title=stream_title,
                    sources=[host],
                    source_url=source_url
                )
                streams.append(stream)
        
        return streams
    
    def _extract_from_video_tags(self, soup: BeautifulSoup, title: str, source_url: str) -> List[Stream]:
        """
        Extract streams from HTML5 video tags
        
        Args:
            soup: BeautifulSoup object
            title: Video title
            source_url: Page URL
        
        Returns:
            List of Stream objects
        """
        streams = []
        
        # Look for video tags
        video_tags = soup.find_all('video')
        
        for video_tag in video_tags:
            # Check for src attribute
            video_src = video_tag.get('src', '')
            if video_src and video_src.startswith('http'):
                stream = Stream(
                    url=video_src,
                    title=title,
                    source_url=source_url
                )
                streams.append(stream)
            
            # Check for source tags inside video
            source_tags = video_tag.find_all('source')
            for source_tag in source_tags:
                src = source_tag.get('src', '')
                if src and src.startswith('http'):
                    stream = Stream(
                        url=src,
                        title=title,
                        source_url=source_url
                    )
                    streams.append(stream)
        
        return streams


# Create singleton instance
mangoporn = MangoPornScraper()


def scrape_mangoporn(query: str, year: Optional[str] = None) -> List[Dict]:
    """
    Function interface for addon.py integration
    
    Args:
        query: Movie search query
        year: Optional year
    
    Returns:
        List of stream dictionaries
    """
    streams = mangoporn.scrape(query, year)
    return [s.to_dict() for s in streams]
