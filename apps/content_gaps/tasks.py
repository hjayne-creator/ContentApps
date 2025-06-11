from celery import shared_task
from .routes import _run_topic_matching_impl
import json
import os
import uuid
from flask import url_for
from flask import current_app
import datetime

@shared_task(name='apps.content_gaps.run_topic_matching')
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
    """Update the task status in the project settings file"""
    project_dir = os.path.join(os.path.dirname(__file__), 'projects', project_id)
    settings_path = os.path.join(project_dir, 'settings.json')
    
    try:
        if os.path.exists(settings_path):
            with open(settings_path, 'r') as f:
                settings = json.load(f)
        else:
            settings = {}
        
        # Initialize jobs list if it doesn't exist
        if 'jobs' not in settings:
            settings['jobs'] = []
            
        # Generate job_id if not provided
        if job_id is None:
            job_id = str(uuid.uuid4())
            
        # Create new job entry
        job = {
            'job_id': job_id,
            'status': status,
            'error_message': error_message,
            'compare_url': compare_url,
            'created_at': str(datetime.datetime.utcnow())
        }
        
        # Remove ALL existing entries for this job_id regardless of status
        settings['jobs'] = [j for j in settings['jobs'] if j['job_id'] != job_id]
        
        # Add the new job entry
        settings['jobs'].append(job)
        
        # Keep only the last 10 jobs
        settings['jobs'] = settings['jobs'][-10:]
        
        # Also update current task status for backward compatibility
        settings['task_status'] = {
            'status': status,
            'error_message': error_message,
            'compare_url': compare_url,
            'job_id': job['job_id']
        }
        
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print(f"Error updating task status: {e}") 