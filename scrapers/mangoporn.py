"""
MangoPorn scraper for Stremio
Migrated from Kodi plugin logic dengan improved robustness
"""

import re
import logging
from typing import List, Optional, Dict
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper, Stream

logger = logging.getLogger(__name__)


class MangoPornScraper(BaseScraper):
    """Scraper untuk mangoporn.net - General adult content"""
    
    SCRAPER_ID = "mangoporn"
    SITE_NAME = "MangoPorn"
    SITE_URL = "https://www.mangoporn.net"
    LOGO_URL = "https://www.google.com/s2/favicons?domain=mangoporn.net&sz=128"
    
    # Fallback selectors untuk handle site layout changes
    SEARCH_ITEM_SELECTORS = [
        ('div.movie-item', 'a.movie-link'),
        ('div.video-item', 'a'),
        ('div.content-item', 'a.title'),
        ('div.item', 'a'),
        ('article', 'h2 a'),
        ('div[class*="post"]', 'a'),
    ]
    
    def search(self, query: str, year: Optional[str] = None, timeout: Optional[int] = None) -> List[Dict]:
        """
        Search untuk movies di MangoPorn
        
        Args:
            query: Movie title or keyword
            year: Optional year
            timeout: Optional timeout
        
        Returns:
            List of movie results
        """
        if not query:
            return []
        
        try:
            # Check cache first
            cache_key = self._make_cache_key("mangoporn_search", query, year or "")
            cached = self.cache_get(cache_key)
            if cached:
                logger.debug(f"Returning cached results for: {query}")
                return cached
            
            # Build search URLs
            search_patterns = [
                f"{self.SITE_URL}/search?q={query.replace(' ', '+')}",
                f"{self.SITE_URL}/search/{query.replace(' ', '-')}",
                f"{self.SITE_URL}/?s={query.replace(' ', '+')}",
            ]
            
            results = []
            
            for search_url in search_patterns:
                logger.info(f"Searching MangoPorn: {search_url[:60]}")
                
                response = self.http_get(search_url, timeout=timeout or self.REQUEST_TIMEOUT)
                if not response:
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Try each selector pattern
                items = self._find_items(soup)
                
                if not items:
                    logger.debug(f"No items found with any selector for {search_url}")
                    continue
                
                logger.info(f"Found {len(items)} items with selectors")
                
                for item in items[:20]:
                    try:
                        result = self._parse_item(item)
                        if result:
                            results.append(result)
                            logger.debug(f"Parsed: {result['title']}")
                    except Exception as e:
                        logger.debug(f"Error parsing item: {e}")
                        continue
                
                # Jika found results, tidak perlu coba pattern lain
                if results:
                    logger.info(f"Got {len(results)} results from {search_url}")
                    break
            
            # Cache results
            self.cache_set(cache_key, results)
            
            return results
            
        except Exception as e:
            logger.error(f"MangoPorn search failed: {e}")
            return []
    
    def _find_items(self, soup: BeautifulSoup) -> List:
        """
        Find items menggunakan multiple selector fallback
        
        Args:
            soup: BeautifulSoup object
        
        Returns:
            List of items
        """
        # Try hardcoded selectors first
        for container_selector, item_selector in self.SEARCH_ITEM_SELECTORS:
            try:
                containers = soup.select(container_selector)
                if containers:
                    logger.debug(f"Found {len(containers)} items dengan selector: {container_selector}")
                    return containers
            except:
                continue
        
        # Fallback: find all divs dengan class yang looks like item
        divs = soup.find_all('div', class_=re.compile(r'(movie|video|item|content|post|entry)', re.IGNORECASE))
        if divs:
            logger.debug(f"Found {len(divs)} items dengan regex fallback")
            return divs
        
        logger.warning("No items found dengan any selector")
        return []
    
    def _parse_item(self, item) -> Optional[Dict]:
        """
        Parse single item element
        
        Args:
            item: BeautifulSoup item element
        
        Returns:
            Dict dengan title, url, thumbnail, duration atau None
        """
        try:
            # Extract title
            title_elem = (
                item.find('a', class_=re.compile(r'title', re.IGNORECASE)) or
                item.find('h2') or
                item.find('h3') or
                item.find('a')
            )
            
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            if not title:
                return None
            
            # Extract URL
            url = title_elem.get('href', '')
            if not url:
                return None
            
            # Make absolute URL
            if not url.startswith('http'):
                url = self.SITE_URL + url if url.startswith('/') else f"{self.SITE_URL}/{url}"
            
            # Validate URL
            if url == self.SITE_URL or not url.startswith('http'):
                return None
            
            # Extract thumbnail
            thumb_elem = item.find('img')
            thumbnail = ""
            if thumb_elem:
                thumbnail = thumb_elem.get('src') or thumb_elem.get('data-src') or ""
            
            # Extract duration
            duration_match = re.search(r'\d+:\d+', str(item))
            duration = duration_match.group(0) if duration_match else ""
            
            return {
                'title': title[:100],  # Limit title length
                'url': url,
                'thumbnail': thumbnail,
                'duration': duration
            }
            
        except Exception as e:
            logger.debug(f"Error parsing item: {e}")
            return None
    
    def get_streams(self, video_url: str) -> List[Stream]:
        """
        Extract playable streams dari MangoPorn movie page
        
        Args:
            video_url: URL of the movie page
        
        Returns:
            List of Stream objects
        """
        if not video_url:
            return []
        
        try:
            logger.info(f"Getting streams from: {video_url[:60]}")
            
            response = self.http_get(video_url)
            if not response:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            streams = []
            
            # Extract movie title
            title_elem = soup.find('h1') or soup.find('title')
            page_title = title_elem.get_text(strip=True) if title_elem else "Unknown"
            if not page_title or page_title == "Unknown":
                # Try to extract from URL
                page_title = video_url.split('/')[-1].replace('-', ' ')[:50]
            
            # Method 1: Extract dari iframes
            iframes = soup.find_all('iframe')
            logger.debug(f"Found {len(iframes)} iframes")
            
            for iframe in iframes:
                iframe_src = iframe.get('src', '')
                if iframe_src:
                    if iframe_src.startswith('//'):
                        iframe_src = 'https:' + iframe_src
                    
                    host = self._get_host_from_url(iframe_src)
                    
                    stream = Stream(
                        url=iframe_src,
                        title=page_title,
                        sources=[host],
                        source_url=video_url
                    )
                    streams.append(stream)
                    logger.debug(f"Added iframe stream: {host}")
            
            # Method 2: Extract dari scripts
            script_streams = self._extract_from_scripts(soup, page_title, video_url)
            streams.extend(script_streams)
            logger.debug(f"Script extraction: {len(script_streams)} streams")
            
            # Method 3: Extract dari players
            player_streams = self._extract_from_players(soup, page_title, video_url)
            streams.extend(player_streams)
            logger.debug(f"Player extraction: {len(player_streams)} streams")
            
            # Method 4: Extract dari links/buttons
            link_streams = self._extract_from_links(soup, page_title, video_url)
            streams.extend(link_streams)
            logger.debug(f"Link extraction: {len(link_streams)} streams")
            
            # Method 5: Extract dari video tags
            video_streams = self._extract_from_video_tags(soup, page_title, video_url)
            streams.extend(video_streams)
            logger.debug(f"Video tag extraction: {len(video_streams)} streams")
            
            # Remove duplicates
            unique_streams = self._deduplicate_streams(streams)
            
            logger.info(f"Extracted {len(unique_streams)} unique streams from {len(streams)} total")
            
            return unique_streams
            
        except Exception as e:
            logger.error(f"Failed to extract streams: {e}")
            return []
    
    def _deduplicate_streams(self, streams: List[Stream]) -> List[Stream]:
        """Remove duplicate streams berdasarkan URL"""
        seen = set()
        unique = []
        for stream in streams:
            if stream.url not in seen:
                seen.add(stream.url)
                unique.append(stream)
        return unique
    
    def _get_host_from_url(self, url: str) -> str:
        """Identify video host dari URL"""
        if not url:
            return "Unknown"
        
        hosts_map = {
            'doodstream': 'DoodStream',
            'filemoon': 'FileMoon',
            'streamwish': 'StreamWish',
            'vidguard': 'Vidguard',
            'player4me': 'Player4Me',
            'vidnest': 'VidNest',
            'lulustream': 'LuluStream',
            'vidhidepro': 'VidHidePro',
            'javggvideo': 'JavggVideo',
        }
        
        url_lower = url.lower()
        for key, value in hosts_map.items():
            if key in url_lower:
                return value
        
        # Extract domain sebagai fallback
        match = re.search(r'https?://(?:www\.)?([^./]+)', url)
        return match.group(1) if match else "Unknown"
    
    def _extract_from_scripts(self, soup: BeautifulSoup, title: str, source_url: str) -> List[Stream]:
        """Extract video sources dari JavaScript"""
        streams = []
        scripts = soup.find_all('script')
        
        for script in scripts:
            if not script.string:
                continue
            
            script_text = script.string
            
            # Look untuk iframe URLs dalam JavaScript
            iframe_urls = re.findall(
                r'https?://[^\s"\']+(?:doodstream|filemoon|lulustream|vidguard|player4me|vidnest)[^\s"\']*',
                script_text,
                re.IGNORECASE
            )
            
            for url in iframe_urls:
                url = re.sub(r'["\'].*$', '', url)
                if url.startswith('http'):
                    host = self._get_host_from_url(url)
                    stream = Stream(
                        url=url,
                        title=title,
                        sources=[host],
                        source_url=source_url
                    )
                    streams.append(stream)
            
            # Look untuk direct video files
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
        """Extract streams dari embedded player divs"""
        streams = []
        
        player_divs = soup.find_all('div', class_=re.compile(r'(player|video-player|embed|media)', re.IGNORECASE))
        
        for player_div in player_divs:
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
        """Extract streams dari download/stream buttons"""
        streams = []
        
        buttons = soup.find_all('a', class_=re.compile(r'(download|stream|play|link|button)', re.IGNORECASE))
        
        for button in buttons:
            href = button.get('href', '')
            btn_text = button.get_text(strip=True)
            
            if href and href.startswith('http'):
                host = self._get_host_from_url(href)
                
                stream_title = btn_text if btn_text else title
                
                stream = Stream(
                    url=href,
                    title=stream_title[:100],
                    sources=[host],
                    source_url=source_url
                )
                streams.append(stream)
        
        return streams
    
    def _extract_from_video_tags(self, soup: BeautifulSoup, title: str, source_url: str) -> List[Stream]:
        """Extract streams dari HTML5 video tags"""
        streams = []
        
        video_tags = soup.find_all('video')
        
        for video_tag in video_tags:
            video_src = video_tag.get('src', '')
            if video_src and video_src.startswith('http'):
                stream = Stream(
                    url=video_src,
                    title=title,
                    source_url=source_url
                )
                streams.append(stream)
            
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
    """Function interface untuk addon.py integration"""
    streams = mangoporn.scrape(query, year)
    return [s.to_dict() for s in streams]
