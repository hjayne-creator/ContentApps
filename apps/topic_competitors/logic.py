import re
import asyncio
import requests
from urllib.parse import urlparse
from decouple import config
from openai import OpenAI
import aiohttp
import time

# Load environment variables
OPENAI_API_KEY = config('OPENAI_API_KEY')
SERPAPI_API_KEY = config('SERPAPI_API_KEY')
SEMRUSH_API_KEY = config('SEMRUSH_API_KEY')
OPENAI_MODEL = config('OPENAI_MODEL', default='gpt-4o-mini')

# Set up OpenAI
try:
    client = OpenAI(api_key=OPENAI_API_KEY)
except TypeError:
    import openai
    openai.api_key = OPENAI_API_KEY
    client = openai

def generate_subtopics(main_topic):
    """Generate 5 related subtopics using OpenAI."""
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a content analyst that generates related subtopics."},
                {"role": "user", "content": f"Generate 5 related subtopics for '{main_topic}'. Return only a list of 5 items, no explanations. Use simple bullet points with dashes (-), not numbered lists."}
            ]
        )
        subtopics_text = response.choices[0].message.content
    except AttributeError:
        response = client.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a content analyst that generates related subtopics."},
                {"role": "user", "content": f"Generate 5 related subtopics for '{main_topic}'. Return only a list of 5 items, no explanations. Use simple bullet points with dashes (-), not numbered lists."}
            ]
        )
        subtopics_text = response.choices[0].message.content
    subtopics = [line.strip() for line in subtopics_text.strip().split('\n') if line.strip()]
    subtopics = [re.sub(r'^\s*(?:\d+\.|-|\*|\+)\s*', '', topic) for topic in subtopics]
    return subtopics[:5]

def generate_keywords(main_topic, subtopics):
    all_topics = [main_topic] + subtopics
    keywords_data = []
    for topic in all_topics:
        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an SEO analyst that generates search keywords."},
                    {"role": "user", "content": f"Generate 3 SEO search keywords for '{topic}'. Keep keywords short and concise, 5 words or less. Return only a list of 3 items, no explanations. Use simple bullet points with dashes (-), not numbered lists."}
                ]
            )
            keywords_text = response.choices[0].message.content
        except AttributeError:
            response = client.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an SEO analyst that generates search keywords."},
                    {"role": "user", "content": f"Generate 3 SEO search keywords for '{topic}'. Keep keywords short and concise, 5 words or less. Return only a list of 3 items, no explanations. Use simple bullet points with dashes (-), not numbered lists."}
                ]
            )
            keywords_text = response.choices[0].message.content
        keywords = [line.strip() for line in keywords_text.strip().split('\n') if line.strip()]
        keywords = [re.sub(r'^\s*(?:\d+\.|-|\*|\+)\s*', '', keyword) for keyword in keywords]
        keywords = [keyword.replace('"', '').replace("'", "") for keyword in keywords]
        for keyword in keywords[:3]:
            keywords_data.append({
                "keyword": keyword,
                "related_topic": topic,
                "volume": 0,
                "top_results": []
            })
    return keywords_data

def get_search_volume(keywords_data):
    api_key = SEMRUSH_API_KEY
    api_url = 'https://api.semrush.com/'
    database = 'us'
    for keyword_data in keywords_data:
        keyword = keyword_data["keyword"]
        params = {
            'type': 'phrase_this',
            'key': api_key,
            'phrase': keyword,
            'database': database,
            'export_columns': 'Ph,Nq',
        }
        try:
            response = requests.get(api_url, params=params)
            if response.status_code == 200:
                lines = response.text.strip().split('\n')
                if len(lines) > 1:
                    headers = [h.strip() for h in lines[0].split(';')]
                    values = [v.strip() for v in lines[1].split(';')]
                    result = dict(zip(headers, values))
                    volume = (
                        result.get('Nq') or
                        result.get('Search Volume') or
                        result.get('Search Volume\r') or
                        '0'
                    )
                    volume = volume.strip().replace('\r', '')
                    keyword_data["volume"] = int(volume) if volume.isdigit() else 0
                else:
                    keyword_data["volume"] = 0
            else:
                keyword_data["volume"] = 0
        except Exception:
            keyword_data["volume"] = 0
    return keywords_data

async def get_serp_data(keywords_data):
    async def fetch_serp_data(session, keyword):
        base_url = "https://serpapi.com/search"
        params = {
            "q": keyword,
            "api_key": SERPAPI_API_KEY,
            "engine": "google",
            "num": 5,
            "hl": "en",
            "gl": "us"
        }
        try:
            async with session.get(base_url, params=params) as response:
                if response.status == 200:
                    results = await response.json()
                    organic_results = results.get("organic_results", [])
                    top_results = []
                    for result in organic_results[:5]:
                        top_results.append({
                            "title": result.get("title", ""),
                            "link": result.get("link", ""),
                            "snippet": result.get("snippet", "")
                        })
                    return top_results
                else:
                    return []
        except Exception:
            return []
    sem = asyncio.Semaphore(5)
    async def fetch_with_semaphore(session, keyword):
        async with sem:
            return await fetch_serp_data(session, keyword)
    async with aiohttp.ClientSession() as session:
        tasks = []
        for keyword_data in keywords_data:
            task = asyncio.create_task(
                fetch_with_semaphore(session, keyword_data["keyword"])
            )
            tasks.append((keyword_data, task))
        for keyword_data, task in tasks:
            keyword_data["top_results"] = await task
    return keywords_data

def analyze_domains(keywords_with_serp):
    domain_counts = {}
    for keyword_data in keywords_with_serp:
        for result in keyword_data["top_results"]:
            url = result["link"]
            domain = urlparse(url).netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            url_lower = url.lower()
            editorial_indicators = [
                "blog", "insights", "resources", "news", "post", "inspiration",
                "guide", "article", "library", "learn", "tips", "advice",
                "top", "best", "types", "pulse"
            ]
            has_editorial_word = any(indicator in url_lower for indicator in editorial_indicators)
            date_pattern = re.search(r"/\\d{4}/\\d{2}(/\\d{2})?/", url_lower)
            path_has_editorial = has_editorial_word or bool(date_pattern)
            if domain in domain_counts:
                domain_counts[domain]["total_appearances"] += 1
                domain_counts[domain]["has_blog"] = domain_counts[domain]["has_blog"] or path_has_editorial
                if url not in domain_counts[domain]["urls"]:
                    domain_counts[domain]["urls"].append(url)
            else:
                domain_counts[domain] = {
                    "domain": domain,
                    "total_appearances": 1,
                    "has_blog": path_has_editorial,
                    "urls": [url]
                }
    for d in domain_counts.values():
        d["count"] = len(d["urls"])
    top_domains = list(domain_counts.values())
    top_domains.sort(key=lambda x: x["total_appearances"], reverse=True)
    return top_domains

def generate_summary(top_domains):
    domains_text = "\n".join([
        f"{d['domain']}: {d['count']} appearances, has editorial content: {d['has_blog']}"
        for d in top_domains[:10]
    ])
    prompt = f"""Based on the following domain frequency analysis for SEO results, \
                create a summary about which domains are dominating organic search \
                for the given topic and whether they have editorial content:\n\n                {domains_text}\n\n                Keep your summary concise but informative."""
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful SEO analyst."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except AttributeError:
        response = client.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful SEO analyst."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip() 