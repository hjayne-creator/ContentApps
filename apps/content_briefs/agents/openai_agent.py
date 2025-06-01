from apps.content_briefs.prompts import OPENAI_KEYWORD_PROMPT
import openai
import re
import json
from apps.content_briefs.config import Config

class OpenAIAgent:
    def __init__(self, api_key):
        self.api_key = api_key
        self.client = openai.OpenAI(api_key=api_key)

    def get_related_keywords(self, keyword):
        prompt = OPENAI_KEYWORD_PROMPT.format(keyword=keyword)
        try:
            response = self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.7
            )
            content = response.choices[0].message.content.strip()
            with open("openai_keyword_debug.log", "a") as f:
                f.write(f"Raw OpenAI keyword response: {content}\n")
            try:
                raw_keywords = json.loads(content)
            except Exception:
                raw_keywords = [line.strip('- ').strip() for line in content.split('\n') if line.strip()]
            def clean_kw(kw):
                kw = re.sub(r'^\s*\d+\.\s*', '', kw)  # Remove leading numbers, dots, spaces
                kw = kw.strip().strip('"').strip("'")  # Remove leading/trailing quotes and whitespace
                return kw
            keywords = [clean_kw(kw) for kw in raw_keywords]
            if keyword not in keywords:
                keywords = [keyword] + keywords
            return keywords[:4]
        except Exception as e:
            print(f"OpenAI error: {e}")
            return [keyword]

    def get_keyword_info(self, keyword):
        prompt = f"Provide a concise, informative summary or explanation for the following keyword, suitable for a blog brief. Limit your response to about 100 words.\n\nKeyword: {keyword}"
        try:
            response = self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,  # ~600 chars, should be about 100 words
                temperature=0.7
            )
            content = response.choices[0].message.content.strip()
            # Optionally trim to 100 words if OpenAI returns more
            words = content.split()
            if len(words) > 100:
                content = ' '.join(words[:100]) + '...'
            return content
        except Exception as e:
            print(f"OpenAI get_keyword_info error: {e}")
            return f"Summary for {keyword} unavailable." 