import os
from apps.content_briefs.prompts import WEBSITE_SUMMARY_PROMPT
import requests
from bs4 import BeautifulSoup
import openai
from apps.content_briefs.config import Config

BROWSER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
}

class CrawlAgent:
    def __init__(self, api_key=None):
        if api_key is None:
            api_key = os.getenv('OPENAI_API_KEY')
        self.client = openai.OpenAI(api_key=api_key)

    def summarize_website(self, url):
        try:
            resp = requests.get(url, headers=BROWSER_HEADERS, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Remove script/style
            for tag in soup(['script', 'style']):
                tag.decompose()
            text = ' '.join(soup.stripped_strings)
            text = text[:1000]
            prompt = WEBSITE_SUMMARY_PROMPT.format(text=text)
            response = self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=120,
                temperature=0.7
            )
            summary = response.choices[0].message.content.strip()
            return summary
        except Exception as e:
            print(f"CrawlAgent summarize_website error: {e}")
            return f"Summary of {url}"

    def extract_headings(self, url): #limit to 10 headings
        try:
            print(f"Fetching: {url}")
            resp = requests.get(url, headers=BROWSER_HEADERS, timeout=10)
            print(f"Status code: {resp.status_code}")
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Get all headings
            h1_tags = soup.find_all('h1')
            h2_tags = soup.find_all('h2')
            
            # Combine all headings into a single list of tuples (text, type)
            all_headings = [(h.get_text(strip=True), 'h1') for h in h1_tags] + \
                         [(h.get_text(strip=True), 'h2') for h in h2_tags]
            
            # Take only the first 10 headings
            limited_headings = all_headings[:10]
            
            # Separate back into h1 and h2 lists
            h1 = [text for text, tag_type in limited_headings if tag_type == 'h1']
            h2 = [text for text, tag_type in limited_headings if tag_type == 'h2']
            
            print(f"H1: {h1}")
            print(f"H2: {h2}")
            return {"h1": h1, "h2": h2}
        except Exception as e:
            print(f"CrawlAgent extract_headings error: {e}")
            return {"h1": [], "h2": [], "error": str(e)}