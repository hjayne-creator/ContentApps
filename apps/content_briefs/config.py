import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev')
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    broker_connection_retry_on_startup = True  # For Celery 6+ compatibility

    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    SERPAPI_API_KEY = os.getenv('SERPAPI_API_KEY', '')
    REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID', '')
    REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET', '')
    REDDIT_USER_AGENT = os.getenv('REDDIT_USER_AGENT', '')
    REDDIT_USERNAME = os.getenv('REDDIT_USERNAME', '')
    REDDIT_PASSWORD = os.getenv('REDDIT_PASSWORD', '')
    BRIEFS_DIR = os.getenv('BRIEFS_DIR', 'briefs')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o')