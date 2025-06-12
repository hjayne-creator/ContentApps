import os

# Base directory for the application
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Projects directory
PROJECTS_DIR = os.path.join(os.path.dirname(__file__), 'projects')

# Get storage directory from environment variable, fallback to default
STORAGE_DIR = os.getenv('CONTENT_GAPS_STORAGE_DIR', os.path.join(BASE_DIR, 'data'))

# Persistent storage directory
PERSISTENT_STORAGE_DIR = os.path.join(STORAGE_DIR, 'content_gaps')

# Ensure the persistent storage directory exists
os.makedirs(PERSISTENT_STORAGE_DIR, exist_ok=True)

# Projects directory within persistent storage
PROJECTS_DIR = os.path.join(PERSISTENT_STORAGE_DIR, 'projects')

# Ensure the projects directory exists
os.makedirs(PROJECTS_DIR, exist_ok=True)
