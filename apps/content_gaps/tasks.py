from celery import shared_task
from .routes import _run_topic_matching_impl
import json
import os
import uuid
from flask import url_for, current_app
import datetime
from .models import ContentGapsJob
from extensions import db
from celery_app import celery

def update_task_status(project_id, status, error_message=None, compare_url=None, job_id=None, tree_id=None, selected_site_ids=None):
    """Helper function to update task status"""
    try:
        # Try to find existing job
        existing_job = ContentGapsJob.query.filter_by(
            project_id=project_id,
            job_id=job_id
        ).first()
        
        if existing_job:
            # Update existing job
            existing_job.status = status
            existing_job.error_message = error_message
            existing_job.compare_url = compare_url
            existing_job.updated_at = datetime.datetime.utcnow()
        else:
            # Create new job
            job = ContentGapsJob(
                project_id=project_id,
                tree_id=tree_id,
                job_id=job_id,
                status=status,
                error_message=error_message,
                compare_url=compare_url,
                selected_site_ids=selected_site_ids,
                created_at=datetime.datetime.utcnow()
            )
            db.session.add(job)
        
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Error updating task status: {e}")
        db.session.rollback()
        raise  # Re-raise the exception to ensure the task fails properly

@celery.task(name='apps.content_gaps.tasks.run_topic_matching')
def run_topic_matching_task(project_id, user_id, topic_tree_id, selected_site_ids=None):
    """
    Celery task wrapper for run_topic_matching function.
    This allows the long-running topic matching process to run in the background.
    
    Args:
        project_id: The ID of the project to run topic matching for
        user_id: The ID of the user running the task
        topic_tree_id: The ID of the topic tree to use for matching
        selected_site_ids: List of site IDs to analyze (if None, all sites will be analyzed)
    """
    # Generate a unique job ID
    job_id = str(uuid.uuid4())
    
    # Update task status to 'RUNNING'
    update_task_status(project_id, 'RUNNING', job_id=job_id, tree_id=topic_tree_id, selected_site_ids=selected_site_ids)
    
    try:
        # Run the implementation
        result = _run_topic_matching_impl(project_id, user_id, topic_tree_id, selected_site_ids)
        
        # Update status with success and compare view information
        # Construct the compare URL manually since we're outside request context
        compare_url = f'/apps/content-gaps/projects/{project_id}/compare/{topic_tree_id}'
        
        # Update task status with the same job_id
        update_task_status(project_id, 'COMPLETED', compare_url=compare_url, job_id=job_id, tree_id=topic_tree_id, selected_site_ids=selected_site_ids)
        return result
    except Exception as e:
        # Update task status with the same job_id
        update_task_status(project_id, 'FAILED', str(e), job_id=job_id, tree_id=topic_tree_id, selected_site_ids=selected_site_ids)
        raise 