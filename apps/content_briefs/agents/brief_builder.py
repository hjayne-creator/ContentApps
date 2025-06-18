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

    def build_brief(self, all_keywords, serp_data, website_summary, serp_headings, reddit_summaries, keyword_info=None):
        """
        Builds a content brief using the collected research data.
        
        Args:
            all_keywords (list): List of related keywords
            serp_data (dict): SERP data for each keyword
            website_summary (str): Summary of the target website
            serp_headings (dict): Headings extracted from SERP results
            reddit_summaries (dict): Reddit discussion summaries
            keyword_info (dict, optional): Additional keyword information
            
        Returns:
            dict: The generated content brief in JSON format
        """
        # Validate input data
        if not isinstance(all_keywords, list) or not all_keywords:
            raise ValueError("all_keywords must be a non-empty list")
        if not isinstance(serp_data, dict):
            raise ValueError("serp_data must be a dictionary")
        if not isinstance(website_summary, str):
            raise ValueError("website_summary must be a string")
        if not isinstance(serp_headings, dict):
            raise ValueError("serp_headings must be a dictionary")
        if not isinstance(reddit_summaries, dict):
            raise ValueError("reddit_summaries must be a dictionary")
            
        # Prepare the research data for the prompt
        research_data = {
            "keywords": {
                "main_keyword": all_keywords[0],
                "related_keywords": all_keywords[1:],
                "metrics": keyword_info or {}
            },
            "serp_analysis": {
                "main_keyword_data": serp_data.get(all_keywords[0], {}),
                "related_keywords_data": {kw: serp_data.get(kw, {}) for kw in all_keywords[1:]}
            },
            "website_context": website_summary,
            "content_structure_analysis": {
                "main_keyword_headings": serp_headings.get(all_keywords[0], []),
                "related_keywords_headings": {kw: serp_headings.get(kw, []) for kw in all_keywords[1:]}
            },
            "audience_insights": {
                "main_keyword_discussions": reddit_summaries.get(all_keywords[0], ""),
                "related_topics": {kw: reddit_summaries.get(kw, "") for kw in all_keywords[1:] if kw in reddit_summaries}
            }
        }
        
        # Convert research data to string format
        data_str = json.dumps(research_data, indent=2)
        
        # Prepare the prompt - using a different approach to avoid format string issues
        prompt = BRIEF_BUILDER_PROMPT.replace("{data}", data_str)
        
        # Call OpenAI API
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert content strategist and SEO specialist."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        # Extract and parse the JSON response
        content = response.choices[0].message.content
        
        # Clean the response to ensure it's valid JSON
        # Remove any markdown code block indicators if present
        content = re.sub(r'```json\n?|\n?```', '', content)
        
        try:
            brief = json.loads(content)
            return brief
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse OpenAI response as JSON: {str(e)}")