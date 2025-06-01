import os
from apps.content_briefs.prompts import BRIEF_BUILDER_PROMPT
import json
import openai
import re
from apps.content_briefs.config import Config

class BriefBuilder:
    def __init__(self, api_key=None):
        if api_key is None:
            api_key = os.getenv('OPENAI_API_KEY')
        self.client = openai.OpenAI(api_key=api_key)

    def build_brief(self, keyword_list, serp_data, website_summary, serp_headings, reddit_summaries, keyword_info=None):
        # TODO: Use OpenAI to generate a structured brief from all agent results
        data = {
            "keywords": keyword_list,
            "serp_data": serp_data,
            "website_summary": website_summary,
            "serp_headings": serp_headings,
            "reddit_summaries": reddit_summaries
        }
        if keyword_info is not None:
            data["keyword_info"] = keyword_info
        prompt = BRIEF_BUILDER_PROMPT.format(data=json.dumps(data, indent=2))
        try:
            response = self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.7
            )
            content = response.choices[0].message.content
            # Try to robustly extract JSON from the response
            def extract_json_from_response(text):
                match = re.search(r'({[\s\S]*})', text)
                if match:
                    json_str = match.group(1)
                    try:
                        return json.loads(json_str)
                    except Exception:
                        pass
                try:
                    return json.loads(text)
                except Exception:
                    return None
            brief = extract_json_from_response(content)
            if brief is not None:
                return brief
            else:
                return {"full_brief": content}
        except Exception as e:
            print(f"BriefBuilder error: {e}")
            return {
                "audience": "Audience profile (placeholder)",
                "search_intent": "Search intent (placeholder)",
                "title": "Suggested Title (placeholder)",
                "introduction": "Introduction paragraph (placeholder)",
                "talking_points": ["Point 1 (placeholder)", "Point 2 (placeholder)"],
                "word_count": 1200,
                "full_brief": prompt
            } 