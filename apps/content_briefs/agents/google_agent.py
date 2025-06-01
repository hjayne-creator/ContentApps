import requests

class GoogleAgent:
    def __init__(self, api_key):
        self.api_key = api_key

    def get_serp_data(self, keyword):
        base_url = "https://serpapi.com/search"
        params = {
            "q": keyword,
            "api_key": self.api_key,
            "engine": "google",
            "num": 5,  # get up to 5 organic results
            "hl": "en",
            "gl": "us"
        }
        try:
            response = requests.get(base_url, params=params, timeout=10)
            if response.status_code == 200:
                results = response.json()
                # Top 5 organic results
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
                return {
                    "serp_results": [],
                    "related_searches": [],
                    "related_questions": []
                }
        except Exception as e:
            print(f"SerpAPI error: {e}")
            return {
                "serp_results": [],
                "related_searches": [],
                "related_questions": []
            } 