import os
import time
import datetime
from apps import db
from apps.topic_competitors.models import TopicCompetitorsJob
from .logic import generate_subtopics, generate_keywords, get_search_volume, get_serp_data, analyze_domains, generate_summary

# This function will be called by RQ or Celery task wrappers

def run_topic_competitor_analysis_logic(job_id):
    job = TopicCompetitorsJob.query.get(job_id)
    if not job:
        return
    start_time = time.time()
    try:
        job.progress = "Generating subtopics..."
        db.session.commit()
        subtopics = generate_subtopics(job.main_topic)
        job.subtopics = subtopics
        db.session.commit()
        job.progress = "Generating keywords..."
        db.session.commit()
        keywords_data = generate_keywords(job.main_topic, subtopics)
        job.keywords = keywords_data
        db.session.commit()
        job.progress = "Fetching search volumes..."
        db.session.commit()
        keywords_with_volume = get_search_volume(keywords_data)
        job.progress = "Fetching SERP data..."
        db.session.commit()
        keywords_with_serp = get_serp_data(keywords_with_volume)
        if hasattr(keywords_with_serp, '__await__'):
            import asyncio
            keywords_with_serp = asyncio.run(get_serp_data(keywords_with_volume))
        job.progress = "Analyzing domains..."
        db.session.commit()
        analysis_results = analyze_domains(keywords_with_serp)
        job.progress = "Generating summary..."
        db.session.commit()
        summary = generate_summary(analysis_results)
        result = {
            "main_topic": job.main_topic,
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
        job.progress = "Completed"
        db.session.commit()
    except Exception as e:
        job.status = "error"
        job.error = str(e)
        job.duration = round(time.time() - start_time, 2)
        job.progress = "Error: " + str(e)
        db.session.commit() 