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
from apps.content_plan.celery_config import celery
from apps.topic_competitors.jobs import run_topic_competitor_analysis
from .logic import generate_subtopics, generate_keywords, get_search_volume, get_serp_data, analyze_domains, generate_summary
from celery.result import AsyncResult

topic_competitors_bp = Blueprint(
    'topic_competitors',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/apps/topic-competitors/static'
)

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

@topic_competitors_bp.route('/')
def index():
    return render_template('topic_competitors_index.html')

@topic_competitors_bp.route('/results', methods=['POST'])
def analyze_topic():
    main_topic = request.form.get('topic')
    user_ip = request.remote_addr
    if not main_topic:
        return jsonify({"error": "No topic provided"}), 400
    job = TopicCompetitorsJob(
        main_topic=main_topic,
        status="queued",
        created_at=datetime.datetime.utcnow(),
        user_ip=user_ip
    )
    db.session.add(job)
    db.session.commit()
    # Enqueue the background job with Celery
    celery_task = run_topic_competitor_analysis.delay(job.id)
    job.celery_task_id = celery_task.id
    db.session.commit()
    # Render a waiting page with job id and celery task id
    return render_template('topic_competitors_waiting.html', job_id=job.id, celery_task_id=celery_task.id)

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

# New route to check job status/results
@topic_competitors_bp.route('/results/status/<int:job_id>')
def topic_competitors_status(job_id):
    job = TopicCompetitorsJob.query.get_or_404(job_id)
    if job.status == 'completed':
        return redirect(url_for('topic_competitors.topic_competitors_results', job_id=job.id))
    return render_template('topic_competitors_waiting.html', job_id=job.id, status=job.status, error=job.error)

@topic_competitors_bp.route('/results/task_status/<task_id>')
def topic_competitors_task_status(task_id):
    res = AsyncResult(task_id, app=celery)
    status = res.status
    response = {'status': status}
    if status == 'SUCCESS':
        # Find the job by celery_task_id
        job = TopicCompetitorsJob.query.filter_by(celery_task_id=task_id).first()
        if job:
            response['redirect_url'] = url_for('topic_competitors.topic_competitors_results', job_id=job.id)
            response['progress'] = job.progress
    elif status == 'FAILURE':
        response['error'] = str(res.result)
    else:
        job = TopicCompetitorsJob.query.filter_by(celery_task_id=task_id).first()
        if job:
            response['progress'] = job.progress
    return jsonify(response)
