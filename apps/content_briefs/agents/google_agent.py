import requests
import time

class GoogleAgent:
    def __init__(self, api_key):
        self.api_key = api_key

    def get_serp_data(self, keyword, max_retries=3):
        base_url = "https://serpapi.com/search"
        params = {
            "q": keyword,
            "api_key": self.api_key,
            "engine": "google",
            "num": 3,  # get up to 5 organic results
            "hl": "en",
            "gl": "us"
        }
        
        for attempt in range(max_retries):
            try:
                # Increased timeout to 30 seconds
                response = requests.get(base_url, params=params, timeout=30)
                if response.status_code == 200:
                    results = response.json()
                    # Top organic results
                    organic_results = results.get("organic_results", [])
                    top_results = []
                    for result in organic_results[:5]:
                        top_results.append({
                            "title": result.get("title", "No title"),
                            "url": result.get("link", ""),
                            "description": result.get("snippet", "No description")
                        })
                    # Top 3 related searches (query only)
                    related_searches = []
                    for rs in results.get("related_searches", [])[:3]:
                        if "query" in rs:
                            related_searches.append({
                                "block_position": rs.get("block_position", 1),
                                "query": rs["query"]
                            })
                    # Top 3 related questions (question only)
                    related_questions = []
                    for rq in results.get("related_questions", [])[:3]:
                        if "question" in rq:
                            related_questions.append({
                                "question": rq["question"]
                            })
                    return {
                        "serp_results": top_results,
                        "related_searches": related_searches,
                        "related_questions": related_questions
                    }
                else:
                    print(f"SerpAPI HTTP error: {response.status_code}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    return {
                        "serp_results": [],
                        "related_searches": [],
                        "related_questions": []
                    }
            except requests.exceptions.Timeout as e:
                print(f"SerpAPI timeout error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                return {
                    "serp_results": [],
                    "related_searches": [],
                    "related_questions": []
                }
            except Exception as e:
                print(f"SerpAPI error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                return {
                    "serp_results": [],
                    "related_searches": [],
                    "related_questions": []
                }
        
        return {
            "serp_results": [],
            "related_searches": [],
            "related_questions": []
        } 