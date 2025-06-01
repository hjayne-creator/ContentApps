from celery_app import celery
from apps.topic_competitors.jobs import run_topic_competitor_analysis_logic

@celery.task(bind=True)
def run_topic_competitor_analysis(self, job_id):
    return run_topic_competitor_analysis_logic(job_id) 