"""
PornWatch scraper untuk Stremio
Migrated dari Kodi plugin dengan robustness improvements
"""

import re
import logging
from typing import List, Optional, Dict
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper, Stream

logger = logging.getLogger(__name__)


class PornWatchScraper(BaseScraper):
    """Scraper untuk pornwatch.ws"""
    
    SCRAPER_ID = "pornwatch"
    SITE_NAME = "PornWatch"
    SITE_URL = "https://www.pornwatch.ws"
    LOGO_URL = "https://www.google.com/s2/favicons?domain=pornwatch.ws&sz=128"
    
    # Fallback selectors
    SEARCH_ITEM_SELECTORS = [
        ('div.scene-item', 'a'),
        ('div.video-item', 'a'),
        ('div.scene', 'a'),
        ('article', 'h2 a'),
        ('div[class*="item"]', 'a'),
    ]
    
    def search(self, query: str, year: Optional[str] = None, timeout: Optional[int] = None) -> List[Dict]:
        """Search untuk scenes di PornWatch"""
        if not query:
            return []
        
        try:
            # Check cache
            cache_key = self._make_cache_key("pornwatch_search", query, year or "")
            cached = self.cache_get(cache_key)
            if cached:
                return cached
            
            search_url = f"{self.SITE_URL}/search?q={query.replace(' ', '+')}"
            logger.info(f"Searching PornWatch: {search_url[:60]}")
            
            response = self.http_get(search_url, timeout=timeout or self.REQUEST_TIMEOUT)
            if not response:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Find items dengan fallback
            items = self._find_items(soup)
            
            if not items:
                logger.debug("No items found")
                return []
            
            logger.info(f"Found {len(items)} items")
            
            for item in items[:10]:
                try:
                    result = self._parse_item(item)
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.debug(f"Error parsing item: {e}")
                    continue
            
            # Cache
            self.cache_set(cache_key, results)
            
            return results
            
        except Exception as e:
            logger.error(f"PornWatch search failed: {e}")
            return []
    
    def _find_items(self, soup: BeautifulSoup) -> List:
        """Find items dengan fallback selectors"""
        for container_selector, item_selector in self.SEARCH_ITEM_SELECTORS:
            try:
                containers = soup.select(container_selector)
                if containers:
                    logger.debug(f"Found {len(containers)} items dengan selector: {container_selector}")
                    return containers
            except:
                continue
        
        # Fallback
        divs = soup.find_all('div', class_=re.compile(r'(scene|video|item|content)', re.IGNORECASE))
        if divs:
            logger.debug(f"Found {len(divs)} items dengan regex fallback")
            return divs
        
        return []
    
    def _parse_item(self, item) -> Optional[Dict]:
        """Parse single item"""
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
            
            # Make absolute
            if not url.startswith('http'):
                url = self.SITE_URL + url if url.startswith('/') else f"{self.SITE_URL}/{url}"
            
            if url == self.SITE_URL or not url.startswith('http'):
                return None
            
            # Extract thumbnail
            thumb_elem = item.find('img')
            thumbnail = ""
            if thumb_elem:
                thumbnail = thumb_elem.get('src') or thumb_elem.get('data-src') or ""
            
            return {
                'title': title[:100],
                'url': url,
                'thumbnail': thumbnail
            }
            
        except Exception as e:
            logger.debug(f"Error parsing item: {e}")
            return None
    
    def get_streams(self, video_url: str) -> List[Stream]:
        """Extract streams dari PornWatch scene page"""
        if not video_url:
            return []
        
        try:
            logger.info(f"Getting streams from: {video_url[:60]}")
            
            response = self.http_get(video_url)
            if not response:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            streams = []
            
            # Extract title
            title_elem = soup.find('h1') or soup.find('title')
            page_title = title_elem.get_text(strip=True) if title_elem else "Unknown"
            if not page_title or page_title == "Unknown":
                page_title = video_url.split('/')[-1].replace('-', ' ')[:50]
            
            # Method 1: Iframes
            iframes = soup.find_all('iframe')
            logger.debug(f"Found {len(iframes)} iframes")
            
            for iframe in iframes:
                iframe_src = iframe.get('src', '')
                if iframe_src:
                    if iframe_src.startswith('//'):
                        iframe_src = 'https:' + iframe_src
                    
                    logger.debug(f"Found iframe: {iframe_src[:50]}")
                    
                    host = self._get_host_from_url(iframe_src)
                    
                    stream = Stream(
                        url=iframe_src,
                        title=page_title,
                        sources=[host],
                        source_url=video_url
                    )
                    streams.append(stream)
            
            # Method 2: Scripts
            script_streams = self._extract_from_scripts(soup, page_title, video_url)
            streams.extend(script_streams)
            
            # Method 3: Players
            player_streams = self._extract_from_players(soup, page_title, video_url)
            streams.extend(player_streams)
            
            # Method 4: Links
            link_streams = self._extract_from_links(soup, page_title, video_url)
            streams.extend(link_streams)
            
            # Remove duplicates
            unique_streams = self._deduplicate_streams(streams)
            
            logger.info(f"Extracted {len(unique_streams)} unique streams")
            
            return unique_streams
            
        except Exception as e:
            logger.error(f"Failed to extract streams: {e}")
            return []
    
    def _deduplicate_streams(self, streams: List[Stream]) -> List[Stream]:
        """Remove duplicates"""
        seen = set()
        unique = []
        for stream in streams:
            if stream.url not in seen:
                seen.add(stream.url)
                unique.append(stream)
        return unique
    
    def _get_host_from_url(self, url: str) -> str:
        """Identify host dari URL"""
        if not url:
            return "Unknown"
        
        hosts_map = {
            'doodstream': 'DoodStream',
            'player4me': 'Player4Me',
            'filemoon': 'FileMoon',
            'vidnest': 'VidNest',
            'streamwish': 'StreamWish',
            'lulustream': 'LuluStream',
            'vidhidepro': 'VidHidePro',
            'javggvideo': 'JavggVideo',
            'vidguard': 'Vidguard',
        }
        
        url_lower = url.lower()
        for key, value in hosts_map.items():
            if key in url_lower:
                return value
        
        # Fallback
        match = re.search(r'https?://(?:www\.)?([^./]+)', url)
        return match.group(1) if match else "Unknown"
    
    def _extract_from_scripts(self, soup: BeautifulSoup, title: str, source_url: str) -> List[Stream]:
        """Extract dari scripts"""
        streams = []
        scripts = soup.find_all('script')
        
        for script in scripts:
            if not script.string:
                continue
            
            script_text = script.string
            
            # Find iframe URLs
            iframe_urls = re.findall(
                r'https?://[^\s"\']+(?:doodstream|player4me|filemoon|vidnest|streamwish)[^\s"\']*',
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
            
            # Find video files
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
        """Extract dari players"""
        streams = []
        
        player_divs = soup.find_all('div', class_=re.compile(r'(player|video-player|embed)', re.IGNORECASE))
        
        for player_div in player_divs:
            for attr in ['data-video', 'data-src', 'data-url', 'data-embed']:
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
        """Extract dari links"""
        streams = []
        
        # Find all links yang looks like video hosts
        links = soup.find_all('a', href=re.compile(r'(doodstream|player4me|filemoon|vidnest)', re.IGNORECASE))
        
        for link in links:
            href = link.get('href', '')
            link_text = link.get_text(strip=True)
            
            if href and href.startswith('http'):
                host = self._get_host_from_url(href)
                
                stream_title = link_text if link_text else title
                
                stream = Stream(
                    url=href,
                    title=stream_title[:100],
                    sources=[host],
                    source_url=source_url
                )
                streams.append(stream)
        
        return streams


# Create singleton
pornwatch = PornWatchScraper()


def scrape_pornwatch(query: str, year: Optional[str] = None) -> List[Dict]:
    """Function interface"""
    streams = pornwatch.scrape(query, year)
    return [s.to_dict() for s in streams]
