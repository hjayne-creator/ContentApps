import os
from celery import Celery
from flask import Flask
from extensions import db
from apps import create_app

def init_app():
    """Initialize Flask app and extensions"""
    app = create_app()
    return app

def make_celery(app):
    celery = Celery(
        app.import_name,
        broker=app.config.get('CELERY_BROKER_URL', os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')),
        backend=app.config.get('CELERY_RESULT_BACKEND', os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')),
        broker_connection_retry_on_startup=True
    )
    celery.conf.update(app.config)
    
    class ContextTask(celery.Task):
        abstract = True
        _flask_app = None
        
        @property
        def flask_app(self):
            if self._flask_app is None:
                self._flask_app = init_app()
            return self._flask_app
        
        def __call__(self, *args, **kwargs):
            with self.flask_app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery

# Create the Flask app
flask_app = init_app()

# Initialize Celery with the Flask app
celery = make_celery(flask_app)

# Import all modules that define Celery tasks so they are registered
import apps.content_plan.tasks
import apps.topic_competitors.celery_tasks
import apps.content_briefs.tasks.generate_brief
import apps.content_gaps.tasks
# Add any other task modules here as needed 