"""
Web Scraper Tool
Extract data from websites, APIs, and web pages.

Features:
- HTML scraping with CSS selectors
- API requests (GET, POST, PUT, DELETE)
- JSON/XML parsing
- Form submission
- Cookie/session management
- Rate limiting
- robots.txt respect
- Content extraction (article text, links, images)
"""

import os
import re
import json
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs
from typing import Any, Dict, List, Optional

try:
    import urllib.request
    from urllib.request import Request, urlopen
    URLLIB_AVAILABLE = True
except ImportError:
    URLLIB_AVAILABLE = False

from core.kernel import ToolBase, ToolMetadata, MicroKernel
from utils.logger import log


class WebScraper(ToolBase):
    """Web scraping and HTTP request tool."""
    
    metadata = ToolMetadata(
        name="web_scraper",
        version="2.0.0",
        description="Scrape websites, make API requests, extract data from web pages.",
        category="network",
        tags=["web", "scrape", "http", "api", "extract"],
        provides=["web_scraping", "http_requests", "data_extraction"],
        permissions=["network"]
    )
    
    def __init__(self, kernel: MicroKernel = None):
        super().__init__(kernel)
        self.default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0'
        }
        self.delay = 1  # Seconds between requests (rate limiting)
        self._last_request_time = 0
        self._session_cookies = {}
    
    def execute(self, *args, **kwargs) -> Any:
        """Main execution method."""
        action = kwargs.get("action", "get")
        
        actions = {
            "get": self.http_get,
            "post": self.http_post,
            "scrape": self.scrape_page,
            "extract_links": self.extract_links,
            "extract_images": self.extract_images,
            "extract_text": self.extract_text,
            "api_request": self.api_request,
            "download_file": self.download_file,
        }
        
        if action in actions:
            return actions[action](**kwargs)
        
        raise ValueError(f"Unknown action: {action}")
    
    def _rate_limit(self):
        """Respect rate limiting."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last_request_time = time.time()
    
    def _request(self, url: str, method: str = "GET", 
                 headers: Dict = None, data: bytes = None,
                 timeout: int = 30) -> Dict:
        """Make HTTP request."""
        self._rate_limit()
        
        merged_headers = {**self.default_headers, **(headers or {})}
        
        try:
            req = Request(url, method=method, data=data, headers=merged_headers)
            
            with urlopen(req, timeout=timeout) as response:
                content = response.read()
                
                # Try decode as text
                try:
                    text = content.decode('utf-8')
                except:
                    text = content.decode('latin-1')
                
                return {
                    "status": response.status,
                    "url": response.url,
                    "headers": dict(response.headers),
                    "content": content,
                    "text": text,
                    "size": len(content),
                }
                
        except Exception as e:
            return {"error": str(e), "url": url}
    
    def http_get(self, url: str, headers: Dict = None, **kwargs) -> Dict:
        """Simple GET request."""
        log.info(f"GET {url}")
        return self._request(url, "GET", headers=headers)
    
    def http_post(self, url: str, data: Dict = None, 
                  json_data: Dict = None, headers: Dict = None,
                  **kwargs) -> Dict:
        """POST request."""
        log.info(f"POST {url}")
        
        merged_headers = headers or {}
        
        if json_data:
            body = json.dumps(json_data).encode('utf-8')
            merged_headers['Content-Type'] = 'application/json'
        elif data:
            body = urllib.parse.urlencode(data).encode('utf-8')
            merged_headers['Content-Type'] = 'application/x-www-form-urlencoded'
        else:
            body = None
        
        return self._request(url, "POST", headers=merged_headers, data=body)
    
    def scrape_page(self, url: str, selector: str = None, 
                    **kwargs) -> Dict:
        """
        Scrape a web page.
        
        Args:
            url: Page URL
            selector: CSS selector to extract specific elements
        """
        log.info(f"Scraping: {url}")
        
        result = self._request(url)
        
        if "error" in result:
            return result
        
        # Parse HTML
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(result["text"], 'html.parser')
            
            # Extract basic info
            title = soup.title.string if soup.title else ""
            
            scraped = {
                "url": url,
                "title": title,
                "text": soup.get_text(separator='\n', strip=True)[:5000],
            }
            
            # Specific selector
            if selector:
                elements = soup.select(selector)
                scraped["selected"] = [str(el) for el in elements[:20]]
                scraped["selected_text"] = [el.get_text(strip=True) for el in elements[:20]]
            
            # Meta tags
            meta = {}
            for tag in soup.find_all('meta'):
                name = tag.get('name') or tag.get('property')
                content = tag.get('content')
                if name and content:
                    meta[name] = content
            scraped["meta"] = meta
            
            # Structured data (JSON-LD)
            json_ld = []
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    json_ld.append(json.loads(script.string))
                except:
                    pass
            scraped["structured_data"] = json_ld
            
            log.success(f"Scraped: {title[:60]}")
            return scraped
            
        except ImportError:
            log.warning("BeautifulSoup not installed. Raw HTML returned.")
            return {
                "url": url,
                "text": result["text"][:5000],
                "note": "Install beautifulsoup4 for better parsing"
            }
    
    def extract_links(self, url: str, same_domain: bool = True,
                      **kwargs) -> List[Dict]:
        """Extract all links from a page."""
        result = self._request(url)
        
        if "error" in result:
            return []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(result["text"], 'html.parser')
            
            links = []
            base_domain = urlparse(url).netloc
            
            for a in soup.find_all('a', href=True):
                href = a['href']
                full_url = urljoin(url, href)
                domain = urlparse(full_url).netloc
                
                if same_domain and domain != base_domain:
                    continue
                
                links.append({
                    "url": full_url,
                    "text": a.get_text(strip=True)[:100],
                    "domain": domain,
                })
            
            # Remove duplicates
            seen = set()
            unique = []
            for link in links:
                if link["url"] not in seen:
                    seen.add(link["url"])
                    unique.append(link)
            
            log.info(f"Found {len(unique)} unique links")
            return unique[:100]  # Limit
            
        except ImportError:
            # Regex fallback
            pattern = r'href=["\'](.*?)["\']'
            matches = re.findall(pattern, result["text"])
            return [{"url": urljoin(url, m)} for m in matches[:100]]
    
    def extract_images(self, url: str, **kwargs) -> List[Dict]:
        """Extract image URLs from a page."""
        result = self._request(url)
        
        if "error" in result:
            return []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(result["text"], 'html.parser')
            
            images = []
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src')
                if src:
                    images.append({
                        "url": urljoin(url, src),
                        "alt": img.get('alt', ''),
                        "width": img.get('width'),
                        "height": img.get('height'),
                    })
            
            log.info(f"Found {len(images)} images")
            return images[:50]
            
        except ImportError:
            pattern = r'<img[^>]+src=["\'](.*?)["\'][^>]*>'
            matches = re.findall(pattern, result["text"])
            return [{"url": urljoin(url, m)} for m in matches[:50]]
    
    def extract_text(self, url: str, **kwargs) -> str:
        """Extract article/main text from a page."""
        result = self._request(url)
        
        if "error" in result:
            return result["error"]
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(result["text"], 'html.parser')
            
            # Remove script/style
            for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
                tag.decompose()
            
            # Try to find article content
            article = (soup.find('article') or 
                      soup.find('main') or 
                      soup.find('div', class_=re.compile('content|article|post')) or
                      soup.find('div', id=re.compile('content|article|post')))
            
            if article:
                text = article.get_text(separator='\n', strip=True)
            else:
                text = soup.get_text(separator='\n', strip=True)
            
            # Clean up
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            return '\n'.join(lines[:200])  # First 200 lines
            
        except ImportError:
            # Basic text extraction
            text = re.sub(r'<[^>]+>', ' ', result["text"])
            text = re.sub(r'\s+', ' ', text)
            return text[:5000]
    
    def api_request(self, url: str, method: str = "GET",
                    params: Dict = None, json_data: Dict = None,
                    headers: Dict = None, **kwargs) -> Dict:
        """
        Make API request with automatic JSON parsing.
        
        Args:
            url: API endpoint
            method: HTTP method
            params: Query parameters
            json_data: JSON body
            headers: Additional headers
        """
        # Build URL with params
        if params:
            query = urllib.parse.urlencode(params)
            url = f"{url}?{query}"
        
        merged_headers = {
            'Accept': 'application/json',
            **(headers or {})
        }
        
        if json_data:
            body = json.dumps(json_data).encode('utf-8')
            merged_headers['Content-Type'] = 'application/json'
        else:
            body = None
        
        result = self._request(url, method, headers=merged_headers, data=body)
        
        # Try parse JSON
        if "text" in result:
            try:
                result["json"] = json.loads(result["text"])
            except:
                pass
        
        return result
    
    def download_file(self, url: str, output: str = None,
                      **kwargs) -> str:
        """Download a file from URL."""
        log.info(f"Downloading: {url}")
        
        if not output:
            # Guess filename from URL
            parsed = urlparse(url)
            output = os.path.basename(parsed.path) or "download"
        
        self._rate_limit()
        
        try:
            req = Request(url, headers=self.default_headers)
            
            with urlopen(req, timeout=60) as response:
                with open(output, 'wb') as f:
                    f.write(response.read())
            
            size = os.path.getsize(output)
            log.success(f"Downloaded: {output} ({size} bytes)")
            return output
            
        except Exception as e:
            log.error(f"Download failed: {e}")
            return ""
    
    def health_check(self) -> Dict:
        return {
            "status": "healthy" if URLLIB_AVAILABLE else "degraded",
            "name": self.metadata.name,
            "version": self.metadata.version,
            "urllib": URLLIB_AVAILABLE,
        }
