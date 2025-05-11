import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import time
import random
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging

logger = logging.getLogger(__name__)

def validate_url(url):
    """Validate if the given string is a proper URL."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

def get_random_user_agent():
    """Return a random modern browser user agent."""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15'
    ]
    return random.choice(user_agents)

def create_session():
    """Create a requests session with retry logic."""
    session = requests.Session()
    retry_strategy = Retry(
        total=5,  # increased number of retries
        backoff_factor=2,  # increased backoff time
        status_forcelist=[500, 502, 503, 504, 429, 403, 408],
        allowed_methods=["GET", "POST", "HEAD", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_maxsize=100)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def scrape_website(url):
    """Scrape website for meta title, meta description, and all visible body text."""
    try:
        if not validate_url(url):
            return {
                "success": False,
                "error": "Invalid URL format. Please include http:// or https://"
            }

        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        }
        session = create_session()
        response = session.get(
            url,
            headers=headers,
            timeout=30,
            verify=True,
            allow_redirects=True
        )
        response.raise_for_status()
        content_type = response.headers.get('Content-Type', '').lower()
        if 'text/html' not in content_type:
            return {"success": False, "error": f"Not an HTML page (Content-Type: {content_type})"}

        soup = BeautifulSoup(response.text, 'html.parser')

        title = soup.title.string.strip() if soup.title and soup.title.string else ''
        description = ''
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            description = meta_desc['content'].strip()

        body = soup.body
        body_text = body.get_text(separator=' ', strip=True) if body else ''

        if not (title or description or body_text):
            return {"success": False, "error": "No meaningful content extracted from the page."}
        if len(body_text) < 50:
            return {"success": False, "error": f"Insufficient content retrieved (only {len(body_text)} characters)"}

        # Truncate to ~500 words (8000 chars max)
        words = body_text.split()
        if len(words) > 500:
            body_text = ' '.join(words[:500]) + '... (truncated)'
        if len(body_text) > 4000:
            body_text = body_text[:4000] + '... (truncated)'

        return {
            "success": True,    
            "title": title,
            "description": description,
            "body": body_text
        }
    except requests.exceptions.RequestException as e:
        if isinstance(e, requests.exceptions.ConnectionError):
            return {"success": False, "error": f"Connection error - {str(e)}. The website might be blocking requests or experiencing issues."}
        elif isinstance(e, requests.exceptions.Timeout):
            return {"success": False, "error": f"Request timed out - {str(e)}"}
        elif isinstance(e, requests.exceptions.SSLError):
            return {"success": False, "error": f"SSL error - {str(e)}"}
        else:
            return {"success": False, "error": f"Request failed - {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}