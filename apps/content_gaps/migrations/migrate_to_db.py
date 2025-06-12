import os
import json
import uuid
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create Flask app and configure database
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Import models
from apps.content_gaps.models import TopicTree, Site, Match, ContentGapsJob

def migrate_data():
    with app.app_context():
        # Get all project directories
        projects_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'projects'))
        if not os.path.exists(projects_dir):
            print("Projects directory not found")
            return

        for project_id in os.listdir(projects_dir):
            project_dir = os.path.join(projects_dir, project_id)
            if not os.path.isdir(project_dir):
                continue

            print(f"\nMigrating project: {project_id}")

            # Migrate topic trees
            for fname in os.listdir(project_dir):
                if fname.startswith('topic_tree_') and fname.endswith('.json'):
                    try:
                        with open(os.path.join(project_dir, fname)) as f:
                            tree_data = json.load(f)
                        
                        # Create topic tree in database
                        topic_tree = TopicTree(
                            id=tree_data['tree_id'],
                            project_id=project_id,
                            tree_name=tree_data['tree_name'],
                            root_topic=tree_data['root_topic'],
                            tree_data=tree_data['tree']
                        )
                        db.session.add(topic_tree)
                        print(f"Migrated topic tree: {tree_data['tree_name']}")
                    except Exception as e:
                        print(f"Error migrating topic tree {fname}: {e}")

            # Migrate sites
            for fname in os.listdir(project_dir):
                if fname.startswith('site_') and fname.endswith('.json'):
                    try:
                        with open(os.path.join(project_dir, fname)) as f:
                            site_data = json.load(f)
                        
                        # Create site in database
                        site = Site(
                            id=site_data['site_id'],
                            project_id=project_id,
                            label=site_data.get('label', 'Untitled Site'),
                            is_my_site=site_data.get('is_my_site', False),
                            pages=site_data.get('pages', [])
                        )
                        db.session.add(site)
                        print(f"Migrated site: {site_data.get('label', 'Untitled Site')}")
                    except Exception as e:
                        print(f"Error migrating site {fname}: {e}")

            # Migrate matches
            for fname in os.listdir(project_dir):
                if fname.startswith('matches_') and fname.endswith('.json'):
                    try:
                        tree_id = fname.replace('matches_', '').replace('.json', '')
                        with open(os.path.join(project_dir, fname)) as f:
                            matches_data = json.load(f)
                        
                        # Create matches in database
                        for match in matches_data:
                            match_obj = Match(
                                project_id=project_id,
                                tree_id=tree_id,
                                site_id=match['site_id'],
                                page_index=match['page_index'],
                                matched_topics=match['matched_topics'],
                                similarity_scores=match['similarity_scores']
                            )
                            db.session.add(match_obj)
                        print(f"Migrated matches for tree: {tree_id}")
                    except Exception as e:
                        print(f"Error migrating matches {fname}: {e}")

            # Commit all changes for this project
            try:
                db.session.commit()
                print(f"Successfully migrated project: {project_id}")
            except Exception as e:
                db.session.rollback()
                print(f"Error committing project {project_id}: {e}")

if __name__ == '__main__':
    migrate_data() 