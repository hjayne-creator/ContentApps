from celery import shared_task
from .routes import _run_topic_matching_impl
import json
import os
import uuid
from flask import url_for
from flask import current_app
import datetime
from .models import ContentGapsJob
from apps import db

@shared_task(name='apps.content_gaps.tasks.run_topic_matching')
def run_topic_matching_task(project_id, user_id, topic_tree_id):
    """
    Celery task wrapper for run_topic_matching function.
    This allows the long-running topic matching process to run in the background.
    
    Args:
        project_id: The ID of the project to run topic matching for
        user_id: The ID of the user running the task
        topic_tree_id: The ID of the topic tree to use for matching
    """
    # Generate a unique job ID
    job_id = str(uuid.uuid4())
    
    # Update task status to 'RUNNING'
    update_task_status(project_id, 'RUNNING', job_id=job_id)
    
    try:
        result = _run_topic_matching_impl(project_id, user_id, topic_tree_id)
        # Update status with success and compare view information
        # Construct the compare URL manually since we're outside request context
        compare_url = f'/apps/content-gaps/projects/{project_id}/compare/{topic_tree_id}'
        # Update task status with the same job_id
        update_task_status(project_id, 'COMPLETED', compare_url=compare_url, job_id=job_id)
        return result
    except Exception as e:
        # Update task status with the same job_id
        update_task_status(project_id, 'FAILED', str(e), job_id=job_id)
        raise

def update_task_status(project_id, status, error_message=None, compare_url=None, job_id=None):
    """Update the task status in the database"""
    try:
        # Generate job_id if not provided
        if job_id is None:
            job_id = str(uuid.uuid4())
            
        # Try to find existing job
        job = ContentGapsJob.query.filter_by(
            project_id=project_id,
            job_id=job_id
        ).first()
        
        if job:
            # Update existing job
            job.status = status
            job.error_message = error_message
            job.compare_url = compare_url
            job.updated_at = datetime.datetime.utcnow()
        else:
            # Create new job
            job = ContentGapsJob(
                project_id=project_id,
                job_id=job_id,
                status=status,
                error_message=error_message,
                compare_url=compare_url
            )
            db.session.add(job)
            
        # Commit changes
        db.session.commit()
            
        current_app.logger.info(f"Updated task status for job {job_id} to {status}")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating task status: {e}")
        # Log the error but don't raise it to prevent task failure 