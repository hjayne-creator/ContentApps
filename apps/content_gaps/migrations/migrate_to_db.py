import os
import json
import uuid
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# Import models
from apps.content_gaps.models import Project, TopicTree, Site, Match, ContentGapsJob

def migrate_data():
    """Migrate data from JSON files to database"""
    projects_dir = os.path.join('apps', 'content_gaps', 'projects')
    
    if not os.path.exists(projects_dir):
        print(f"Projects directory not found: {projects_dir}")
        return
    
    # Get list of project directories
    project_dirs = [d for d in os.listdir(projects_dir) 
                   if os.path.isdir(os.path.join(projects_dir, d))]
    
    for project_id in project_dirs:
        project_dir = os.path.join(projects_dir, project_id)
        
        # Read project settings
        settings_file = os.path.join(project_dir, 'settings.json')
        if not os.path.exists(settings_file):
            print(f"Settings file not found for project {project_id}")
            continue
            
        try:
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                
            # Create project
            project = Project(
                id=uuid.UUID(project_id),
                project_name=settings.get('project_name', 'Unnamed Project'),
                created_at=datetime.fromisoformat(settings.get('created_at', datetime.utcnow().isoformat())),
                updated_at=datetime.fromisoformat(settings.get('updated_at', datetime.utcnow().isoformat()))
            )
            db.session.add(project)
            
            # Migrate topic trees
            topic_trees_dir = os.path.join(project_dir, 'topic_trees')
            if os.path.exists(topic_trees_dir):
                for tree_file in os.listdir(topic_trees_dir):
                    if tree_file.endswith('.json'):
                        tree_path = os.path.join(topic_trees_dir, tree_file)
                        with open(tree_path, 'r') as f:
                            tree_data = json.load(f)
                            
                        topic_tree = TopicTree(
                            id=uuid.uuid4(),
                            project_id=project.id,
                            name=tree_data.get('name', os.path.splitext(tree_file)[0]),
                            tree_data=tree_data.get('tree_data', {}),
                            created_at=datetime.fromisoformat(tree_data.get('created_at', datetime.utcnow().isoformat())),
                            updated_at=datetime.fromisoformat(tree_data.get('updated_at', datetime.utcnow().isoformat()))
                        )
                        db.session.add(topic_tree)
            
            # Migrate sites
            sites_dir = os.path.join(project_dir, 'sites')
            if os.path.exists(sites_dir):
                for site_file in os.listdir(sites_dir):
                    if site_file.endswith('.json'):
                        site_path = os.path.join(sites_dir, site_file)
                        with open(site_path, 'r') as f:
                            site_data = json.load(f)
                            
                        site = Site(
                            id=uuid.uuid4(),
                            project_id=project.id,
                            name=site_data.get('name', os.path.splitext(site_file)[0]),
                            url=site_data.get('url', ''),
                            content=site_data.get('content', {}),
                            created_at=datetime.fromisoformat(site_data.get('created_at', datetime.utcnow().isoformat())),
                            updated_at=datetime.fromisoformat(site_data.get('updated_at', datetime.utcnow().isoformat()))
                        )
                        db.session.add(site)
            
            # Migrate matches
            matches_dir = os.path.join(project_dir, 'matches')
            if os.path.exists(matches_dir):
                for match_file in os.listdir(matches_dir):
                    if match_file.endswith('.json'):
                        match_path = os.path.join(matches_dir, match_file)
                        with open(match_path, 'r') as f:
                            match_data = json.load(f)
                            
                        match = Match(
                            id=uuid.uuid4(),
                            project_id=project.id,
                            topic_tree_id=uuid.UUID(match_data.get('topic_tree_id')),
                            site_id=uuid.UUID(match_data.get('site_id')),
                            topic_id=match_data.get('topic_id', ''),
                            topic_name=match_data.get('topic_name', ''),
                            site_url=match_data.get('site_url', ''),
                            site_name=match_data.get('site_name', ''),
                            match_score=match_data.get('match_score', 0.0),
                            match_details=match_data.get('match_details', {}),
                            created_at=datetime.fromisoformat(match_data.get('created_at', datetime.utcnow().isoformat()))
                        )
                        db.session.add(match)
            
            # Migrate jobs
            jobs_file = os.path.join(project_dir, 'jobs.json')
            if os.path.exists(jobs_file):
                with open(jobs_file, 'r') as f:
                    jobs_data = json.load(f)
                    
                for job_data in jobs_data:
                    job = ContentGapsJob(
                        project_id=project.id,
                        job_id=uuid.UUID(job_data.get('job_id')),
                        status=job_data.get('status', 'UNKNOWN'),
                        error_message=job_data.get('error_message'),
                        compare_url=job_data.get('compare_url'),
                        created_at=datetime.fromisoformat(job_data.get('created_at', datetime.utcnow().isoformat())),
                        updated_at=datetime.fromisoformat(job_data.get('updated_at', datetime.utcnow().isoformat()))
                    )
                    db.session.add(job)
            
            # Commit all changes for this project
            db.session.commit()
            print(f"Successfully migrated project: {project_id}")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error migrating project {project_id}: {e}")

if __name__ == '__main__':
    with app.app_context():
        migrate_data() 