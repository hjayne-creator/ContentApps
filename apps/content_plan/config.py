import os
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Load environment variables from .env file
# Only load if we're not in production (where Render.com provides the environment)
if not os.environ.get('RENDER'):
    load_dotenv()

class Config:
    """Base configuration."""
    # Check if we're in debug mode
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    FLASK_DEBUG=True

    # Database configuration
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = None  # Will be set in init_app
    
    # Generate a random secret key if not provided
    if 'SECRET_KEY' not in os.environ:
        logging.warning("SECRET_KEY not found in environment variables. Using a random key.")
        import secrets
        os.environ['SECRET_KEY'] = secrets.token_hex(16)
    
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # API keys
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    SERPAPI_API_KEY = os.environ.get('SERPAPI_API_KEY')
    
    # Log warnings if API keys are missing
    if not OPENAI_API_KEY:
        logging.warning("OPENAI_API_KEY not found in environment variables. OpenAI functionality will not work.")
    
    if not SERPAPI_API_KEY:
        logging.warning("SERPAPI_API_KEY not found in environment variables. Search functionality will use mock data.")
    
    # Default OpenAI model
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
    OPENAI_MODEL_FALLBACK = 'gpt-4'
    
    # Application settings
    MAX_WEBSITE_CONTENT_LENGTH = int(os.environ.get('MAX_WEBSITE_CONTENT_LENGTH', 20000))
    RESULTS_PER_KEYWORD = int(os.environ.get('RESULTS_PER_KEYWORD', 5))
    
    # Security settings
    WTF_CSRF_ENABLED = True
    
    @classmethod
    def init_app(cls, app):
        """Initialize application with this configuration."""
        # Set up database URL
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            if os.environ.get('RENDER'):
                raise ValueError("DATABASE_URL must be set in production environment")
            logging.warning("DATABASE_URL not found in environment variables, using local development database")
            db_url = 'postgresql://localhost/contentplan'
        
        # Convert postgres:// to postgresql:// for SQLAlchemy
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        
        logging.info(f"Using database URL: {db_url}")
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url
        
        # Log the configuration (without sensitive values)
        logging.info("Application initialized with:")
        logging.info(f"- Debug mode: {cls.DEBUG}")
        logging.info(f"- OpenAI API key set: {'Yes' if cls.OPENAI_API_KEY else 'No'}")
        logging.info(f"- SerpAPI key set: {'Yes' if cls.SERPAPI_API_KEY else 'No'}")
        logging.info(f"- Using OpenAI model: {cls.OPENAI_MODEL}")

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    
    # In development, we can use mock data if API keys are missing
    USE_MOCK_DATA = os.environ.get('USE_MOCK_DATA', 'False').lower() in ('true', '1', 't')
    
    @classmethod
    def init_app(cls, app):
        super().init_app(app)
        logging.info("Running in DEVELOPMENT mode")
        if cls.USE_MOCK_DATA:
            logging.info("Using mock data for API responses")

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    
    @classmethod
    def init_app(cls, app):
        super().init_app(app)
        logging.info("Running in PRODUCTION mode")

# Default to development configuration
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

# Set which configuration to use based on environment variable
def get_config():
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])