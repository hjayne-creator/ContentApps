import requests
from bs4 import BeautifulSoup

if __name__ == "__main__":
    url = "https://funinthesunkeywest.com/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        h1 = [h.get_text(strip=True) for h in soup.find_all('h1')]
        h2 = [h.get_text(strip=True) for h in soup.find_all('h2')]
        print(f"Headings for {url}:")
        print("H1:", h1)
        print("H2:", h2)
    except Exception as e:
        print(f"Error fetching or parsing {url}: {e}") 