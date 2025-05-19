from flask import Blueprint, Flask, render_template, request, jsonify, flash, redirect, url_for
import os
from openai import OpenAI
import requests
import json
from decouple import config
from urllib.parse import urlparse
import re
import aiohttp
import asyncio
from typing import List, Dict
import time
from apps.topic_competitors.models import TopicCompetitorsJob
from apps import db
import datetime

topic_competitors_bp = Blueprint(
    'topic_competitors',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/apps/topic-competitors/static'
)

@topic_competitors_bp.route('/')
def index():
    return render_template('topic_competitors_index.html')

# Load environment variables
OPENAI_API_KEY = config('OPENAI_API_KEY')
SERPAPI_API_KEY = config('SERPAPI_API_KEY')
SEMRUSH_API_KEY = config('SEMRUSH_API_KEY')
OPENAI_MODEL = config('OPENAI_MODEL', default='gpt-4o-mini')  # Default to gpt-model

# Set up OpenAI
try:
    # For newer OpenAI package versions
    client = OpenAI(api_key=OPENAI_API_KEY)
except TypeError:
    # Fallback for older versions or different configurations
    import openai
    openai.api_key = OPENAI_API_KEY
    client = openai

@topic_competitors_bp.route('/results', methods=['POST'])
def analyze_topic():
    main_topic = request.form.get('topic')
    user_ip = request.remote_addr
    start_time = time.time()
    if not main_topic:
        return jsonify({"error": "No topic provided"}), 400
    job = TopicCompetitorsJob(
        main_topic=main_topic,
        status="processing",
        created_at=datetime.datetime.utcnow(),
        user_ip=user_ip
    )
    db.session.add(job)
    db.session.commit()
    try:
        subtopics = generate_subtopics(main_topic)
        job.subtopics = subtopics
        db.session.commit()
        keywords_data = generate_keywords(main_topic, subtopics)
        job.keywords = keywords_data
        db.session.commit()
        keywords_with_volume = get_search_volume(keywords_data)
        keywords_with_serp = asyncio.run(get_serp_data(keywords_with_volume))
        analysis_results = analyze_domains(keywords_with_serp)
        summary = generate_summary(analysis_results)
        # Prepare final result
        result = {
            "main_topic": main_topic,
            "subtopics": subtopics,
            "keywords": keywords_with_serp,
            "top_domains": analysis_results,
            "summary": summary
        }
        job.result = result
        job.summary = summary
        job.top_domains = analysis_results
        job.status = "completed"
        job.duration = round(time.time() - start_time, 2)
        db.session.commit()
        return render_template('topic_competitors_results.html', result=result)
    except Exception as e:
        job.status = "error"
        job.error = str(e)
        job.duration = round(time.time() - start_time, 2)
        db.session.commit()
        return jsonify({"error": str(e)}), 500

def generate_subtopics(main_topic):
    """Generate 5 related subtopics using OpenAI."""
    try:
        # New OpenAI API format
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a content analyst that generates related subtopics."},
                {"role": "user", "content": f"Generate 5 related subtopics for '{main_topic}'. Return only a list of 5 items, no explanations. Use simple bullet points with dashes (-), not numbered lists."}
            ]
        )
        subtopics_text = response.choices[0].message.content
    except AttributeError:
        # Old OpenAI API format
        response = client.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a content analyst that generates related subtopics."},
                {"role": "user", "content": f"Generate 5 related subtopics for '{main_topic}'. Return only a list of 5 items, no explanations. Use simple bullet points with dashes (-), not numbered lists."}
            ]
        )
        subtopics_text = response.choices[0].message.content
    
    # Clean up the response to get a list of subtopics
    subtopics = [line.strip() for line in subtopics_text.strip().split('\n') if line.strip()]
    
    # More thorough cleaning to remove any list formatting (both numbers and bullet points)
    subtopics = [re.sub(r'^\s*(?:\d+\.|-|\*|\+)\s*', '', topic) for topic in subtopics]
    
    return subtopics[:5]  # Ensure we only get 5 subtopics

def generate_keywords(main_topic, subtopics):
    """Generate 5 keywords for each topic and subtopic."""
    all_topics = [main_topic] + subtopics
    keywords_data = []
    
    for topic in all_topics:
        try:
            # New OpenAI API format
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an SEO analyst that generates search keywords."},
                    {"role": "user", "content": f"Generate 3 SEO search keywords for '{topic}'. Keep keywords short and concise, 5 words or less. Return only a list of 3 items, no explanations. Use simple bullet points with dashes (-), not numbered lists."}
                ]
            )
            keywords_text = response.choices[0].message.content
        except AttributeError:
            # Old OpenAI API format
            response = client.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an SEO analyst that generates search keywords."},
                    {"role": "user", "content": f"Generate 3 SEO search keywords for '{topic}'. Keep keywords short and concise, 5 words or less. Return only a list of 3 items, no explanations. Use simple bullet points with dashes (-), not numbered lists."}
                ]
            )
            keywords_text = response.choices[0].message.content
        
        # Clean up the response to get a list of keywords
        keywords = [line.strip() for line in keywords_text.strip().split('\n') if line.strip()]
        
        # More thorough cleaning to remove any list formatting (both numbers and bullet points)
        keywords = [re.sub(r'^\s*(?:\d+\.|-|\*|\+)\s*', '', keyword) for keyword in keywords]
        
        # Remove any quotation marks from the keywords
        keywords = [keyword.replace('"', '').replace("'", "") for keyword in keywords]
        
        for keyword in keywords[:3]:  # Ensure we only get 3 keywords
            keywords_data.append({
                "keyword": keyword,
                "related_topic": topic,
                "volume": 0,  # Will be populated later
                "top_results": []  # Will be populated later
            })
    
    return keywords_data

def get_search_volume(keywords_data):
    """Get search volume for each keyword using SemRush API."""
    api_key = config('SEMRUSH_API_KEY')
    api_url = 'https://api.semrush.com/'
    database = 'us'  # Default to US database
    
    for keyword_data in keywords_data:
        keyword = keyword_data["keyword"]
        
        # API request parameters
        params = {
            'type': 'phrase_this',
            'key': api_key,
            'phrase': keyword,
            'database': database,
            'export_columns': 'Ph,Nq',  # Ph = phrase, Nq = search volume
        }
        
        try:
            # Send request to SemRush API
            response = requests.get(api_url, params=params)
            
            if response.status_code == 200:
                # Parse the response
                lines = response.text.strip().split('\n')
                if len(lines) > 1:
                    headers = [h.strip() for h in lines[0].split(';')]
                    values = [v.strip() for v in lines[1].split(';')]
                    result = dict(zip(headers, values))
                    
                    # Try all possible keys for search volume
                    volume = (
                        result.get('Nq') or
                        result.get('Search Volume') or
                        result.get('Search Volume\r') or
                        '0'
                    )
                    # Remove any stray whitespace or carriage returns
                    volume = volume.strip().replace('\r', '')
                    keyword_data["volume"] = int(volume) if volume.isdigit() else 0
                else:
                    keyword_data["volume"] = 0
            else:
                keyword_data["volume"] = 0
                print(f"Error fetching volume for '{keyword}': {response.status_code}")
        except Exception as e:
            keyword_data["volume"] = 0
            print(f"Exception fetching volume for '{keyword}': {str(e)}")
    
    return keywords_data

async def get_serp_data(keywords_data: List[Dict]) -> List[Dict]:
    """Get SERP data for each keyword using SerpAPI concurrently."""
    async def fetch_serp_data(session: aiohttp.ClientSession, keyword: str) -> List[Dict]:
        base_url = "https://serpapi.com/search"
        params = {
            "q": keyword,
            "api_key": SERPAPI_API_KEY,
            "engine": "google",
            "num": 5,  # Get top 5 results
            "hl": "en",  # Language: English
            "gl": "us"   # Country: United States
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
                    print(f"Error fetching SERP data for '{keyword}': {response.status}")
                    return []
        except Exception as e:
            print(f"Exception fetching SERP data for '{keyword}': {str(e)}")
            return []

    # Create a semaphore to limit concurrent requests
    sem = asyncio.Semaphore(5)  # Limit to 5 concurrent requests
    
    async def fetch_with_semaphore(session: aiohttp.ClientSession, keyword: str) -> List[Dict]:
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
    """Analyze domain frequency and check for editorial content."""
    domain_counts = {}
    
    for keyword_data in keywords_with_serp:
        for result in keyword_data["top_results"]:
            url = result["link"]
            
            # Extract domain
            domain = urlparse(url).netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Check if URL contains indicators of editorial content or a date pattern
            url_lower = url.lower()
            # Editorial indicators
            editorial_indicators = [
                "blog", "insights", "resources", "news", "post", "inspiration",
                "guide", "article", "library", "learn", "tips", "advice",
                "top", "best", "types", "pulse"
            ]
            has_editorial_word = any(indicator in url_lower for indicator in editorial_indicators)
            # Date pattern: /YYYY/MM/ or /YYYY/MM/DD/
            date_pattern = re.search(r"/\\d{4}/\\d{2}(/\\d{2})?/", url_lower)
            path_has_editorial = has_editorial_word or bool(date_pattern)
            
            # Update domain counts
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
    
    # Set count to number of unique URLs
    for d in domain_counts.values():
        d["count"] = len(d["urls"])
    
    top_domains = list(domain_counts.values())
    top_domains.sort(key=lambda x: x["total_appearances"], reverse=True)
    return top_domains

def generate_summary(top_domains):
    """Generate a summary of the analysis using OpenAI."""
    domains_text = "\n".join([
        f"{d['domain']}: {d['count']} appearances, has editorial content: {d['has_blog']}"
        for d in top_domains[:10]
    ])
    
    prompt = f"""Based on the following domain frequency analysis for SEO results, 
                create a summary about which domains are dominating organic search 
                for the given topic and whether they have editorial content:
                
                {domains_text}
                
                Keep your summary concise but informative."""
    
    try:
        # New OpenAI API format
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful SEO analyst."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except AttributeError:
        # Old OpenAI API format
        response = client.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful SEO analyst."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()

@topic_competitors_bp.route('/admin/jobs')
def admin_jobs():
    jobs = TopicCompetitorsJob.query.order_by(TopicCompetitorsJob.created_at.desc()).all()
    return render_template('admin/topic_competitors_jobs.html', jobs=jobs)

@topic_competitors_bp.route('/admin/jobs/cleanup', methods=['POST'])
def cleanup_jobs():
    try:
        # Delete all jobs except completed ones
        num_deleted = TopicCompetitorsJob.query.filter(TopicCompetitorsJob.status != 'completed').delete()
        db.session.commit()
        flash(f'Successfully deleted {num_deleted} incomplete jobs.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting jobs: {str(e)}', 'error')
    return redirect(url_for('topic_competitors.admin_jobs'))

@topic_competitors_bp.route('/results/<int:job_id>')
def topic_competitors_results(job_id):
    job = TopicCompetitorsJob.query.get_or_404(job_id)
    return render_template('topic_competitors_results.html', result=job.result)
