import os
from apps.content_briefs.prompts import REDDIT_SUMMARY_PROMPT
import praw
import openai
from apps.content_briefs.config import Config

class RedditAgent:
    def __init__(self, client_id, client_secret, user_agent, username=None, password=None, api_key=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self.username = username or os.getenv('REDDIT_USERNAME')
        self.password = password or os.getenv('REDDIT_PASSWORD')
        reddit_kwargs = {
            'client_id': client_id,
            'client_secret': client_secret,
            'user_agent': user_agent
        }
        if self.username and self.password:
            reddit_kwargs['username'] = self.username
            reddit_kwargs['password'] = self.password
        self.reddit = praw.Reddit(**reddit_kwargs)
        if api_key is None:
            api_key = os.getenv('OPENAI_API_KEY')
        self.client = openai.OpenAI(api_key=api_key)

    def summarize_discussions(self, keyword):
        prompt = REDDIT_SUMMARY_PROMPT.format(keyword=keyword)
        try:
            posts = self.reddit.subreddit('all').search(keyword, limit=5, sort='relevance')
            discussions = []
            for post in posts:
                discussions.append(post.title + ": " + (post.selftext[:200] if post.selftext else ""))
            text = '\n'.join(discussions)
            if not text:
                text = "No relevant discussions found."
            full_prompt = prompt + "\n\n" + text
            response = self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[{"role": "user", "content": full_prompt}],
                max_tokens=150,
                temperature=0.7
            )
            summary = response.choices[0].message.content.strip()
            return summary
        except Exception as e:
            print(f"RedditAgent error: {e}")
            return prompt 