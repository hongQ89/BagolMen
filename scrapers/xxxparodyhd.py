"""
XXXParodyHD scraper untuk Stremio
Migrated dari Kodi plugin dengan improved robustness
"""

import re
import logging
from typing import List, Optional, Dict
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper, Stream

logger = logging.getLogger(__name__)


class XXXParodyHDScraper(BaseScraper):
    """Scraper untuk xxxparodyhd.net - Parody adult content"""
    
    SCRAPER_ID = "xxxparodyhd"
    SITE_NAME = "XXXParodyHD"
    SITE_URL = "https://www.xxxparodyhd.net"
    LOGO_URL = "https://www.google.com/s2/favicons?domain=xxxparodyhd.net&sz=128"
    
    # Fallback selectors
    SEARCH_ITEM_SELECTORS = [
        ('div.movie-item', 'a.movie-link'),
        ('div.video-item', 'a'),
        ('div.item', 'a'),
        ('article', 'h2 a'),
        ('div[class*="post"]', 'a'),
    ]
    
    def search(self, query: str, year: Optional[str] = None, timeout: Optional[int] = None) -> List[Dict]:
        """Search untuk parody movies di XXXParodyHD"""
        if not query:
            return []
        
        try:
            # Check cache
            cache_key = self._make_cache_key("xxxparodyhd_search", query, year or "")
            cached = self.cache_get(cache_key)
            if cached:
                return cached
            
            search_url = f"{self.SITE_URL}/search/{query.replace(' ', '+')}"
            logger.info(f"Searching XXXParodyHD: {search_url[:60]}")
            
            response = self.http_get(search_url, timeout=timeout or self.REQUEST_TIMEOUT)
            if not response:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Find items dengan fallback selectors
            items = self._find_items(soup)
            
            if not items:
                logger.debug("No items found")
                return []
            
            logger.info(f"Found {len(items)} items")
            
            for item in items[:15]:
                try:
                    result = self._parse_item(item)
                    if result:
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
    
    def _find_items(self, soup: BeautifulSoup) -> List:
        """Find items menggunakan fallback selectors"""
        for container_selector, item_selector in self.SEARCH_ITEM_SELECTORS:
            try:
                containers = soup.select(container_selector)
                if containers:
                    logger.debug(f"Found {len(containers)} items dengan selector: {container_selector}")
                    return containers
            except:
                continue
        
        # Fallback
        divs = soup.find_all('div', class_=re.compile(r'(movie|video|item|post|entry)', re.IGNORECASE))
        if divs:
            logger.debug(f"Found {len(divs)} items dengan regex fallback")
            return divs
        
        return []
    
    def _parse_item(self, item) -> Optional[Dict]:
        """Parse single item element"""
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
            
            if url == self.SITE_URL or not url.startswith('http'):
                return None
            
            # Extract thumbnail
            thumb_elem = item.find('img')
            thumbnail = ""
            if thumb_elem:
                thumbnail = thumb_elem.get('src') or thumb_elem.get('data-src') or ""
            
            # Extract quality
            quality_match = re.search(r'(\d{3,4}p)', str(item))
            quality = quality_match.group(1) if quality_match else "720p"
            
            return {
                'title': title[:100],
                'url': url,
                'thumbnail': thumbnail,
                'quality': quality
            }
            
        except Exception as e:
            logger.debug(f"Error parsing item: {e}")
            return None
    
    def get_streams(self, video_url: str) -> List[Stream]:
        """Extract playable streams dari XXXParodyHD movie page"""
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
            
            # Extract quality
            quality = self._extract_quality(soup)
            
            # Method 1: Iframes
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
                        quality=quality,
                        sources=[host],
                        source_url=video_url
                    )
                    streams.append(stream)
            
            # Method 2: Scripts
            script_streams = self._extract_from_scripts(soup, page_title, quality, video_url)
            streams.extend(script_streams)
            
            # Method 3: Players
            player_streams = self._extract_from_players(soup, page_title, quality, video_url)
            streams.extend(player_streams)
            
            # Method 4: Links
            link_streams = self._extract_from_links(soup, page_title, quality, video_url)
            streams.extend(link_streams)
            
            # Remove duplicates
            unique_streams = self._deduplicate_streams(streams)
            
            logger.info(f"Extracted {len(unique_streams)} unique streams")
            
            return unique_streams
            
        except Exception as e:
            logger.error(f"Failed to extract streams: {e}")
            return []
    
    def _deduplicate_streams(self, streams: List[Stream]) -> List[Stream]:
        """Remove duplicate streams"""
        seen = set()
        unique = []
        for stream in streams:
            if stream.url not in seen:
                seen.add(stream.url)
                unique.append(stream)
        return unique
    
    def _extract_quality(self, soup: BeautifulSoup) -> str:
        """Extract video quality dari page"""
        quality_patterns = ['1080p', '720p', '480p', '360p', 'HD', 'SD']
        
        page_text = soup.get_text()
        for quality in quality_patterns:
            if quality in page_text:
                return quality
        
        return "720p"
    
    def _get_host_from_url(self, url: str) -> str:
        """Identify video host dari URL"""
        if not url:
            return "Unknown"
        
        hosts_map = {
            'doodstream': 'DoodStream',
            'streamwish': 'StreamWish',
            'vidhidepro': 'VidHidePro',
            'javggvideo': 'JavggVideo',
            'filemoon': 'FileMoon',
            'player4me': 'Player4Me',
            'vidnest': 'VidNest',
            'lulustream': 'LuluStream',
            'vidguard': 'Vidguard',
        }
        
        url_lower = url.lower()
        for key, value in hosts_map.items():
            if key in url_lower:
                return value
        
        # Fallback
        match = re.search(r'https?://(?:www\.)?([^./]+)', url)
        return match.group(1) if match else "Unknown"
    
    def _extract_from_scripts(self, soup: BeautifulSoup, title: str, quality: str, source_url: str) -> List[Stream]:
        """Extract dari JavaScript"""
        streams = []
        scripts = soup.find_all('script')
        
        for script in scripts:
            if not script.string:
                continue
            
            script_text = script.string
            
            # Find iframe URLs
            iframe_urls = re.findall(
                r'https?://[^\s"\']+(?:doodstream|streamwish|vidhidepro|javggvideo|filemoon|player4me)[^\s"\']*',
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
                        quality=quality,
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
                    quality=quality,
                    source_url=source_url
                )
                streams.append(stream)
        
        return streams
    
    def _extract_from_players(self, soup: BeautifulSoup, title: str, quality: str, source_url: str) -> List[Stream]:
        """Extract dari player containers"""
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
                        quality=quality,
                        sources=[host],
                        source_url=source_url
                    )
                    streams.append(stream)
        
        return streams
    
    def _extract_from_links(self, soup: BeautifulSoup, title: str, quality: str, source_url: str) -> List[Stream]:
        """Extract dari link sections"""
        streams = []
        
        link_sections = soup.find_all('div', class_=re.compile(r'(link|stream|download)', re.IGNORECASE))
        
        for section in link_sections:
            links = section.find_all('a')
            
            for link in links:
                href = link.get('href', '')
                link_text = link.get_text(strip=True)
                
                if href and href.startswith('http'):
                    host = self._get_host_from_url(href)
                    
                    stream_title = link_text if link_text else title
                    
                    stream = Stream(
                        url=href,
                        title=stream_title[:100],
                        quality=quality,
                        sources=[host],
                        source_url=source_url
                    )
                    streams.append(stream)
        
        return streams


# Create singleton
xxxparodyhd = XXXParodyHDScraper()


def scrape_xxxparodyhd(query: str, year: Optional[str] = None) -> List[Dict]:
    """Function interface untuk addon.py"""
    streams = xxxparodyhd.scrape(query, year)
    return [s.to_dict() for s in streams]
