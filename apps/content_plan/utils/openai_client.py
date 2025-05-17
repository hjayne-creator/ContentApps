from openai import OpenAI
from flask import current_app
import httpx

def get_openai_client():
    """Get an initialized OpenAI client with API key from config"""
    api_key = current_app.config.get('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OpenAI API key not found in configuration")
    
    # Create a custom httpx client without proxies
    http_client = httpx.Client()
    
    # Initialize OpenAI client with the custom http client
    return OpenAI(
        api_key=api_key,
        http_client=http_client
    ) 