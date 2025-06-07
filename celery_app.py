import os
from celery import Celery

def make_celery(app):
    celery = Celery(
        app.import_name,
        broker=app.config.get('CELERY_BROKER_URL', os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')),
        backend=app.config.get('CELERY_RESULT_BACKEND', os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'))
    )
    celery.conf.update(app.config)
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery

# Import and create the Flask app only after defining make_celery to avoid circular import
from apps import create_app
flask_app = create_app()
celery = make_celery(flask_app)

# Import all modules that define Celery tasks so they are registered
import apps.content_plan.tasks
import apps.topic_competitors.celery_tasks
import apps.content_briefs.tasks.generate_brief
import apps.content_gaps.tasks
# Add any other task modules here as needed 