import requests
import os
import json
import time
from flask import current_app
from requests.exceptions import RequestException, Timeout, ConnectionError

def search_serpapi(query, api_key=None, num_results=5, max_retries=3, retry_delay=5, request_delay=3):
    """
    Search using SerpAPI and return results with retry logic
    
    Args:
        query (str): Search query
        api_key (str): SerpAPI API key (optional, will use from config if not provided)
        num_results (int): Number of results to return
        max_retries (int): Maximum number of retry attempts
        retry_delay (int): Delay in seconds between retries (default: 5)
        request_delay (int): Delay in seconds between consecutive requests (default: 3)
    
    Returns:
        list: List of search result dictionaries
    
    Raises:
        ValueError: If API key is not found
        requests.exceptions.RequestException: If API request fails after all retries
    """
    try:
        # Get API key from parameter, app config, or environment
        if not api_key:
            api_key = current_app.config.get('SERPAPI_API_KEY') or os.environ.get('SERPAPI_API_KEY')
        
        # Add debug logging
        current_app.logger.info(f"Using SerpAPI key: {api_key}")
        
        if not api_key:
            raise ValueError("SerpAPI key not found in environment or app config")
        
        # Set up request parameters
        base_url = "https://serpapi.com/search"
        params = {
            "q": query,
            "api_key": api_key,
            "engine": "google",
            "num": num_results,
            "hl": "en",  # Language: English
            "gl": "us"  # Country: United States
        }
        
        # Add delay between consecutive requests to avoid rate limiting
        # This is separate from retry delay and helps with multiple keyword searches
        time.sleep(request_delay)
        
        # Retry logic
        for attempt in range(max_retries):
            try:
                # Make the request with increased timeout
                response = requests.get(base_url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                # Add detailed logging of the response
                current_app.logger.info(f"SerpAPI Response for query '{query}':")
                current_app.logger.info(f"Response status: {response.status_code}")
                current_app.logger.info(f"Response keys: {list(data.keys())}")
                if "organic_results" in data:
                    current_app.logger.info(f"Number of organic results: {len(data['organic_results'])}")
                if "inline_videos" in data:
                    current_app.logger.info(f"Number of video results: {len(data['inline_videos'])}")
                
                # Extract and format results
                results = []
                
                # Check for organic results
                if "organic_results" in data:
                    for result in data["organic_results"]:
                        entry = {
                            "title": result.get("title", ""),
                            "link": result.get("link", ""),
                            "snippet": result.get("snippet", ""),
                            "position": result.get("position", 0),
                            "displayed_link": result.get("displayed_link", ""),
                            "source": result.get("source", "")
                        }
                        results.append(entry)
                
                # Also check for inline videos if available
                if "inline_videos" in data:
                    for video in data["inline_videos"]:
                        entry = {
                            "title": video.get("title", ""),
                            "link": video.get("link", ""),
                            "snippet": f"Video by {video.get('channel', '')} - Duration: {video.get('duration', '')}",
                            "position": video.get("position", 0),
                            "type": "video"
                        }
                        results.append(entry)
                
                # If no results found, check for error message
                if not results:
                    if "error" in data:
                        error_msg = data.get("error", "Unknown error")
                        if attempt < max_retries - 1:
                            current_app.logger.warning(f"SerpAPI error for query '{query}': {error_msg}. Retrying in {retry_delay} seconds...")
                            time.sleep(retry_delay)
                            continue
                        raise RequestException(f"SerpAPI error: {error_msg}")
                    else:
                        # Check for specific response patterns
                        if "search_metadata" in data and data.get("search_metadata", {}).get("status") == "No results":
                            current_app.logger.warning(f"No results found in SerpAPI response for query: {query} (explicit no results status)")
                        elif "organic_results" in data and not data["organic_results"]:
                            current_app.logger.warning(f"Empty organic results array for query: {query}")
                        elif "organic_results" not in data:
                            current_app.logger.warning(f"No organic_results field in response for query: {query}")
                        else:
                            current_app.logger.warning(f"No results found in SerpAPI response for query: {query}")
                        return []
                
                return results
                
            except Timeout:
                if attempt < max_retries - 1:
                    current_app.logger.warning(f"Timeout for query '{query}'. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                raise
            except ConnectionError:
                if attempt < max_retries - 1:
                    current_app.logger.warning(f"Connection error for query '{query}'. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                raise
            except RequestException as e:
                if attempt < max_retries - 1:
                    current_app.logger.warning(f"Request error for query '{query}': {str(e)}. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                raise
    
    except ValueError as e:
        current_app.logger.error(f"Error with SerpAPI configuration: {str(e)}")
        raise
    except Exception as e:
        current_app.logger.error(f"Unexpected error with SerpAPI: {str(e)}")
        raise

def deduplicate_results(results):
    """
    Deduplicate search results by URL
    
    Args:
        results (list): List of search result dictionaries
    
    Returns:
        list: Deduplicated list of search results
    """
    seen_urls = set()
    unique_results = []
    
    for result in results:
        url = result.get("link", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(result)
    
    return unique_results

# Optional: Add mock search function for development/testing
def mock_search(query, num_results=5):
    """Mock search function for development and testing"""
    mock_results = [
        {
            "title": f"Mock Result 1 for {query}",
            "link": "https://example.com/result1",
            "snippet": f"This is a mock search result for {query} with some sample text for testing purposes.",
            "position": 1
        },
        {
            "title": f"Mock Result 2 for {query}",
            "link": "https://example.com/result2",
            "snippet": f"Another mock result for testing the {query} search functionality without using real API calls.",
            "position": 2
        }
    ]
    
    # Generate additional mock results if needed
    for i in range(3, num_results + 1):
        mock_results.append({
            "title": f"Mock Result {i} for {query}",
            "link": f"https://example.com/result{i}",
            "snippet": f"Sample search result #{i} for query: {query}",
            "position": i
        })
    
    return mock_results[:num_results]