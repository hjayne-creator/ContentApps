import os
import json
import pytest
from .routes import run_topic_matching, PROJECTS_DIR, content_gaps_bp
from flask import Flask
from dotenv import load_dotenv

@pytest.fixture
def app():
    # Load environment variables
    load_dotenv()
    
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.secret_key = os.getenv('FLASK_SECRET_KEY', 'test-secret-key')
    
    # Register the blueprint
    app.register_blueprint(content_gaps_bp)
    
    return app

@pytest.fixture
def test_project_data():
    # Create a test project directory
    project_id = "test_project"
    project_dir = os.path.join(PROJECTS_DIR, project_id)
    os.makedirs(project_dir, exist_ok=True)
    
    # Create a test topic tree
    topic_tree = {
        "tree_id": "test_tree",
        "tree_name": "Test Tree",
        "root_topic": "Technology",
        "tree": [
            {
                "name": "Programming",
                "children": [
                    {
                        "name": "Python",
                        "children": [
                            {"name": "Web Development"},
                            {"name": "Data Science"}
                        ]
                    }
                ]
            }
        ]
    }
    
    # Create a test site
    site_data = {
        "site_id": "test_site",
        "label": "Test Site",
        "is_my_site": True,
        "pages": [
            {
                "title": "Python Web Development Guide",
                "description": "Learn how to build web applications with Python",
                "url": "http://example.com/python-web"
            },
            {
                "title": "Data Science with Python",
                "description": "Introduction to data science using Python",
                "url": "http://example.com/python-data"
            }
        ]
    }
    
    # Save the test data
    with open(os.path.join(project_dir, "topic_tree_test_tree.json"), "w") as f:
        json.dump(topic_tree, f)
    
    with open(os.path.join(project_dir, "site_test_site.json"), "w") as f:
        json.dump(site_data, f)
    
    yield project_id
    
    # Cleanup
    import shutil
    shutil.rmtree(project_dir)

def test_run_topic_matching(app, test_project_data, capsys):
    with app.test_request_context(
        method='POST',
        data={'topic_tree_id': 'test_tree'}
    ):
        # Run the matching
        response = run_topic_matching(test_project_data)
        
        # Get the captured output
        captured = capsys.readouterr()
        print("\nDebug Output:")
        print(captured.out)
        
        # Check if matches file was created
        matches_path = os.path.join(PROJECTS_DIR, test_project_data, "matches_test_tree.json")
        assert os.path.exists(matches_path)
        
        # Load and verify matches
        with open(matches_path) as f:
            matches = json.load(f)
        
        # Print match information
        print("\nMatch Information:")
        print(f"Number of matches found: {len(matches)}")
        for i, match in enumerate(matches):
            print(f"\nMatch {i + 1}:")
            print(f"Site ID: {match['site_id']}")
            print(f"Page Index: {match['page_index']}")
            print(f"Matched Topics: {match['matched_topics']}")
            print(f"Similarity Scores: {match['similarity_scores']}")
        
        # Should have matches for both pages
        assert len(matches) == 2
        
        # Verify the structure of matches
        for match in matches:
            assert 'site_id' in match
            assert 'page_index' in match
            assert 'matched_topics' in match
            assert 'similarity_scores' in match
            assert len(match['matched_topics']) == len(match['similarity_scores'])
        
        # First page should have matches (since it contains "Web Development")
        assert len(matches[0]['matched_topics']) > 0, "No matches found for first page"
        
        # Second page should have matches (since it contains "Data Science")
        assert len(matches[1]['matched_topics']) > 0, "No matches found for second page"
        
        # Verify specific matches
        # First page should match "Web Development" topic
        assert any('0' in path for path in matches[0]['matched_topics']), "First page should match Programming topic"
        assert any('0' in path and '1' in path for path in matches[0]['matched_topics']), "First page should match Python topic"
        assert any('0' in path and '1' in path and '0' in path for path in matches[0]['matched_topics']), "First page should match Web Development topic"
        
        # Second page should match "Data Science" topic
        assert any('0' in path for path in matches[1]['matched_topics']), "Second page should match Programming topic"
        assert any('0' in path and '1' in path for path in matches[1]['matched_topics']), "Second page should match Python topic"
        assert any('0' in path and '1' in path and '1' in path for path in matches[1]['matched_topics']), "Second page should match Data Science topic" 