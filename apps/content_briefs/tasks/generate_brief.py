import os
import json
import time
from celery_app import celery
from apps.content_briefs.agents.openai_agent import OpenAIAgent
from apps.content_briefs.agents.google_agent import GoogleAgent
from apps.content_briefs.agents.crawl_agent import CrawlAgent
from apps.content_briefs.agents.reddit_agent import RedditAgent
from apps.content_briefs.agents.brief_builder import BriefBuilder
from apps.content_briefs.config import Config

BRIEFS_DIR = Config.BRIEFS_DIR
os.makedirs(BRIEFS_DIR, exist_ok=True)

@celery.task(bind=True)
def generate_brief_task(self, keyword, website):
    # 1. OpenAI Agent: get keyword research
    self.update_state(state='PROGRESS', meta={'step': 1, 'message': 'Researching the focus keyword...'})
    openai_agent = OpenAIAgent(Config.OPENAI_API_KEY)
    all_keywords = openai_agent.get_related_keywords(keyword)
    keyword_info = openai_agent.get_keyword_info(keyword)
    time.sleep(1)

    # 2. Google Agent: get SERP data for all keywords
    self.update_state(state='PROGRESS', meta={'step': 2, 'message': 'Collecting Google results...'})
    google_agent = GoogleAgent(Config.SERPAPI_API_KEY)
    serp_data = {kw: google_agent.get_serp_data(kw) for kw in all_keywords}
    time.sleep(1)

    # 3. Crawl Agent (SERP): extract headings from SERP URLs
    self.update_state(state='PROGRESS', meta={'step': 3, 'message': 'Analyzing sites returned from Google...'})
    crawl_agent = CrawlAgent()
    serp_headings = {}
    for kw, data in serp_data.items():
        serp_headings[kw] = [crawl_agent.extract_headings(r['url']) for r in data['serp_results']]
    time.sleep(1)

    # 4. Reddit Agent: summarize Reddit discussions for main keyword only
    self.update_state(state='PROGRESS', meta={'step': 4, 'message': 'Analyzing Reddit discussions...'})
    reddit_agent = RedditAgent(
        Config.REDDIT_CLIENT_ID,
        Config.REDDIT_CLIENT_SECRET,
        Config.REDDIT_USER_AGENT,
        Config.REDDIT_USERNAME,
        Config.REDDIT_PASSWORD,
        Config.OPENAI_API_KEY
    )
    main_keyword = all_keywords[0]
    reddit_summaries = {main_keyword: reddit_agent.summarize_discussions(main_keyword)}
    time.sleep(1)

    # 5. Crawl Agent (Website): summarize user website
    self.update_state(state='PROGRESS', meta={'step': 5, 'message': 'Creating a brand profile...'})
    website_summary = crawl_agent.summarize_website(website)
    time.sleep(1)

    # 6. Brief Builder: combine all results
    brief_builder = BriefBuilder()
    brief = brief_builder.build_brief(all_keywords, serp_data, website_summary, serp_headings, reddit_summaries, keyword_info=keyword_info)

    # Save both research data and final brief
    task_id = self.request.id
    
    # Save research data
    result_data = {
        "all_keywords": all_keywords,
        "serp_data": serp_data,
        "serp_headings": serp_headings,
        "reddit_summaries": reddit_summaries,
        "website_summary": website_summary,
        "keyword_info": keyword_info,
        "website_url": website
    }
    research_path = os.path.join(BRIEFS_DIR, f'research_{task_id}.json')
    with open(research_path, 'w') as f:
        json.dump(result_data, f, indent=2)
    
    # Save final brief
    brief_path = os.path.join(BRIEFS_DIR, f'brief_{task_id}.json')
    with open(brief_path, 'w') as f:
        json.dump(brief, f, indent=2)

    return {'result': f'Brief generated!', 'brief_path': brief_path, 'research_path': research_path} 