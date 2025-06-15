from apps import create_app
from celery_app import celery

# This file is used by Render to start the Celery worker
# It imports and re-exports the Celery instance from the shared celery_app.py 

# Create the Flask app and push the app context
flask_app = create_app()
flask_app.app_context().push()

if __name__ == '__main__':
    celery.start() 