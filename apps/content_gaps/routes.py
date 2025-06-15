from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
import os
import uuid
import json
import openai
import csv
from werkzeug.utils import secure_filename
import numpy as np
from dotenv import load_dotenv
from .models import ContentGapsJob, TopicTree, Site, Match, db, Project
from io import TextIOWrapper, StringIO
load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o')

content_gaps_bp = Blueprint('content_gaps', __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/apps/content-gaps/static',
    url_prefix='/apps/content-gaps')

def generate_topic_tree_llm(root_topic):
    if not OPENAI_API_KEY:
        return None, 'OpenAI API key not set.'
    prompt = (
        f"Build a comprehensive 3-level deep topic tree from this topic: '{root_topic}'. "
        "Return the tree as a JSON array of objects, where each node has 'name' and optional 'children'. "
        "Example: [{\"name\":\"Root\",\"children\":[{\"name\":\"Subtopic\",\"children\":[...]}, ...]}]"
    )
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.7
        )
        content = response.choices[0].message.content.strip()
        # Try to extract JSON from the response
        try:
            tree = json.loads(content)
        except Exception:
            # Try to extract JSON substring
            import re
            match = re.search(r'(\[.*\])', content, re.DOTALL)
            if match:
                try:
                    tree = json.loads(match.group(1))
                except Exception:
                    tree = []
            else:
                tree = []
        if not isinstance(tree, list):
            tree = []
        return tree, None
    except Exception as e:
        return [], f'OpenAI error: {e}'

@content_gaps_bp.route('/')
def index():
    projects = Project.query.all()
    projects_data = [{
        'project_id': project.id,
        'project_name': project.project_name,
        'primary_url': project.primary_url,
        'is_my_site': project.is_my_site
    } for project in projects]
    return render_template('content_gaps_index.html', projects=projects_data)

@content_gaps_bp.route('/projects/new', methods=['GET', 'POST'])
def create_project():
    if request.method == 'POST':
        project_name = request.form.get('project_name', '').strip()
        primary_url = request.form.get('primary_url', '').strip()
        is_my_site = bool(request.form.get('is_my_site'))
        if not project_name or not primary_url:
            flash('Project name and primary website URL are required.')
            return render_template('project_new.html')
        
        try:
            project = Project(
                id=str(uuid.uuid4()),
                project_name=project_name,
                primary_url=primary_url,
                is_my_site=is_my_site
            )
            db.session.add(project)
            db.session.commit()
            return redirect(url_for('content_gaps.view_project', project_id=project.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating project: {e}')
            return render_template('project_new.html')
    return render_template('project_new.html')

@content_gaps_bp.route('/projects/<project_id>')
def view_project(project_id):
    # Get project from database
    project = Project.query.get_or_404(project_id)
    
    # Get topic trees from database
    topic_trees = TopicTree.query.filter_by(project_id=project_id).all()
    topic_trees_data = []
    for tree in topic_trees:
        # Check if matches exist for this tree
        has_matches = Match.query.filter_by(project_id=project_id, tree_id=tree.id).first() is not None
        topic_trees_data.append({
            'tree_id': tree.id,
            'tree_name': tree.tree_name,
            'root_topic': tree.root_topic,
            'has_report': has_matches
        })
    
    # Get sites from database
    sites = Site.query.filter_by(project_id=project_id).all()
    sites_data = [{
        'site_id': site.id,
        'label': site.label,
        'is_my_site': site.is_my_site,
        'pages': site.pages
    } for site in sites]
    
    # Get recent job statuses
    job_statuses = ContentGapsJob.query.filter_by(project_id=project_id).order_by(ContentGapsJob.created_at.desc()).limit(10).all()
    
    return render_template('project_view.html', 
                         project_id=project_id, 
                         project=project, 
                         topic_trees=topic_trees_data, 
                         sites=sites_data,
                         jobs=job_statuses)

@content_gaps_bp.route('/projects/<project_id>/topic-trees/new', methods=['GET', 'POST'])
def create_topic_tree(project_id):
    if request.method == 'POST':
        tree_name = request.form.get('tree_name', '').strip()
        root_topic = request.form.get('root_topic', '').strip()
        if not tree_name or not root_topic:
            flash('Tree name and root topic are required.')
            return render_template('topic_tree_new.html', project_id=project_id)
        
        tree, error = generate_topic_tree_llm(root_topic)
        if error:
            flash(error)
            tree = []
        
        # Create new topic tree in database
        topic_tree = TopicTree(
            project_id=project_id,
            tree_name=tree_name,
            root_topic=root_topic,
            tree_data=tree
        )
        
        try:
            db.session.add(topic_tree)
            db.session.commit()
            return redirect(url_for('content_gaps.edit_topic_tree', project_id=project_id, tree_id=topic_tree.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating topic tree: {e}')
            return render_template('topic_tree_new.html', project_id=project_id)
    
    return render_template('topic_tree_new.html', project_id=project_id)

@content_gaps_bp.route('/projects/<project_id>/topic-trees/<tree_id>/edit', methods=['GET', 'POST'])
def edit_topic_tree(project_id, tree_id):
    topic_tree = TopicTree.query.filter_by(id=tree_id, project_id=project_id).first_or_404()
    
    if request.method == 'POST':
        tree_json = request.form.get('tree_json', '')
        try:
            new_tree = json.loads(tree_json)
            topic_tree.tree_data = new_tree
            db.session.commit()
            flash('Tree saved successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving tree: {e}')
    
    tree_data = {
        'tree_id': topic_tree.id,
        'tree_name': topic_tree.tree_name,
        'root_topic': topic_tree.root_topic,
        'tree': topic_tree.tree_data
    }
    
    return render_template('topic_tree_edit_v.html', project_id=project_id, tree_id=tree_id, tree_data=tree_data)

@content_gaps_bp.route('/projects/<project_id>/topic-trees/<tree_id>/edit-vertical', methods=['GET', 'POST'])
def edit_topic_tree_vertical(project_id, tree_id):
    topic_tree = TopicTree.query.filter_by(id=tree_id, project_id=project_id).first_or_404()
    tree_data = {
        'tree_name': topic_tree.tree_name,
        'root_topic': topic_tree.root_topic,
        'tree': topic_tree.tree_data
    }
    
    if request.method == 'POST':
        tree_json = request.form.get('tree_json', '')
        try:
            new_tree = json.loads(tree_json)
            topic_tree.tree_data = new_tree
            db.session.commit()
            flash('Tree saved successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving tree: {e}')
    
    return render_template('topic_tree_edit_v.html', project_id=project_id, tree_id=tree_id, tree_data=tree_data)

@content_gaps_bp.route('/projects/<project_id>/sites/upload', methods=['GET', 'POST'])
def upload_site_content(project_id):
    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('No file uploaded')
            return redirect(request.url)
        
        file = request.files['csv_file']
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
        
        if not file.filename.endswith('.csv'):
            flash('Please upload a CSV file')
            return redirect(request.url)
        
        try:
            # Read the file content and decode it
            content = file.read().decode('utf-8-sig')  # utf-8-sig handles BOM
            csv_file = StringIO(content)
            
            # Try to detect the delimiter
            first_line = csv_file.readline().strip()
            csv_file.seek(0)  # Reset file pointer
            
            # Check if the line contains tabs or commas
            if '\t' in first_line:
                delimiter = '\t'
            else:
                delimiter = ','
            
            reader = csv.DictReader(csv_file, delimiter=delimiter)
            
            # Get the fieldnames (column headers)
            fieldnames = reader.fieldnames
            
            # Directly access the columns we know exist
            url_col = 'Address'
            title_col = 'Title 1'
            desc_col = 'Meta Description 1'
            
            # Verify the columns exist
            if not all(col in fieldnames for col in [url_col, title_col, desc_col]):
                missing_cols = [col for col in [url_col, title_col, desc_col] if col not in fieldnames]
                flash(f'Required columns not found: {", ".join(missing_cols)}. Found columns: {", ".join(fieldnames)}')
                return redirect(request.url)
            
            # Reset file pointer to read data
            csv_file.seek(0)
            reader = csv.DictReader(csv_file, delimiter=delimiter)
            
            pages = []
            for row in reader:
                if row[url_col] and row[title_col] and row[desc_col]:
                    pages.append({
                        'url': row[url_col].strip(),
                        'title': row[title_col].strip(),
                        'description': row[desc_col].strip()
                    })
            
            if not pages:
                flash('No valid pages found in CSV. Please ensure the CSV contains non-empty values for URL, title, and description.')
                return redirect(request.url)
            
            # Create new site in database
            site = Site(
                id=str(uuid.uuid4()),
                project_id=project_id,
                label=request.form.get('site_label', file.filename.replace('.csv', '')),
                is_my_site=bool(request.form.get('is_my_site')),
                pages=pages
            )
            db.session.add(site)
            db.session.commit()
            
            flash('Site content uploaded successfully')
            return redirect(url_for('content_gaps.view_project', project_id=project_id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error processing CSV: {str(e)}")
            flash(f'Error processing file: {e}')
            return redirect(request.url)
            
    return render_template('site_upload.html', project_id=project_id)

@content_gaps_bp.route('/projects/<project_id>/run-matching', methods=['POST'])
def run_topic_matching(project_id):
    topic_tree_id = request.form.get('topic_tree_id')
    selected_site_ids = request.form.getlist('site_ids[]')
    
    if not topic_tree_id:
        flash('Topic tree ID is required.', 'error')
        return redirect(url_for('content_gaps.view_project', project_id=project_id))
    
    if not selected_site_ids:
        flash('Please select at least one site to analyze.', 'error')
        return redirect(url_for('content_gaps.view_project', project_id=project_id))
        
    # Start the background task
    from .tasks import run_topic_matching_task
    task = run_topic_matching_task.delay(project_id, request.user.id if hasattr(request, 'user') else None, topic_tree_id, selected_site_ids)
    
    flash('Topic matching has started in the background. This may take several minutes to complete.', 'info')
    return redirect(url_for('content_gaps.view_project', project_id=project_id))

def _run_topic_matching_impl(project_id, user_id=None, topic_tree_id=None, selected_site_ids=None):
    """Implementation of topic matching logic"""
    from flask import current_app
    
    with current_app.app_context():
        # Get topic tree from database
        topic_tree = TopicTree.query.filter_by(id=topic_tree_id, project_id=project_id).first()
        if not topic_tree:
            raise ValueError(f"Topic tree {topic_tree_id} not found")
        
        # Get selected sites from database
        if selected_site_ids:
            sites = Site.query.filter(Site.id.in_(selected_site_ids), Site.project_id == project_id).all()
        else:
            sites = Site.query.filter_by(project_id=project_id).all()
            
        if not sites:
            raise ValueError("No sites found for this project")
        
        current_app.logger.info(f"Starting topic matching for project {project_id}, tree {topic_tree_id}")
        current_app.logger.info(f"Found {len(sites)} sites to process")
        
        def flatten_tree(nodes, parent_path=None):
            """Flatten the topic tree into a list of paths"""
            if parent_path is None:
                parent_path = []
            paths = []
            for idx, node in enumerate(nodes):
                current_path = parent_path + [str(idx)]
                paths.append(current_path)
                if 'children' in node:
                    paths.extend(flatten_tree(node['children'], current_path))
            return paths
        
        def get_embedding(text):
            """Get embedding for text using OpenAI API"""
            if not OPENAI_API_KEY:
                raise ValueError("OpenAI API key not set")
            try:
                client = openai.OpenAI(api_key=OPENAI_API_KEY)
                response = client.embeddings.create(
                    model="text-embedding-ada-002",
                    input=text
                )
                return response.data[0].embedding
            except Exception as e:
                raise ValueError(f"Error getting embedding: {e}")
        
        def cosine_sim(a, b):
            """Calculate cosine similarity between two vectors"""
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        
        # Get all topic paths
        topic_paths = flatten_tree(topic_tree.tree_data)
        current_app.logger.info(f"Generated {len(topic_paths)} topic paths")
        
        # Get embeddings for all topics
        topic_embeddings = {}
        for path in topic_paths:
            try:
                # Validate path indices and build path string safely
                current_node = topic_tree.tree_data
                path_parts = []
                for idx in path:
                    idx_int = int(idx)
                    if idx_int >= len(current_node):
                        current_app.logger.warning(f"Invalid index {idx_int} in path {path}, skipping")
                        break
                    path_parts.append(current_node[idx_int]['name'])
                    if 'children' in current_node[idx_int]:
                        current_node = current_node[idx_int]['children']
                    else:
                        current_node = []
                
                if path_parts:  # Only process if we have valid path parts
                    path_str = '/'.join(path_parts)
                    topic_embeddings['-'.join(path)] = get_embedding(path_str)
            except Exception as e:
                current_app.logger.error(f"Error processing path {path}: {str(e)}")
                continue
        
        if not topic_embeddings:
            raise ValueError("No valid topic embeddings could be generated")
        
        current_app.logger.info(f"Generated embeddings for {len(topic_embeddings)} topics")
        
        # Process each site
        total_matches = 0
        for site in sites:
            current_app.logger.info(f"Processing site {site.id} with {len(site.pages)} pages")
            # Clear existing matches for this site and tree
            Match.query.filter_by(project_id=project_id, tree_id=topic_tree.id, site_id=site.id).delete()
            
            # Process each page in the site
            for page_idx, page in enumerate(site.pages):
                # Get embedding for page content
                page_embedding = get_embedding(page['description'])
                
                # Find best matching topic
                best_match = None
                best_score = -1
                for topic_path, topic_embedding in topic_embeddings.items():
                    score = cosine_sim(page_embedding, topic_embedding)
                    if score > best_score:
                        best_score = score
                        best_match = topic_path
                
                # Create match record if score is above threshold
                if best_score > 0.5:  # Lowered threshold to get more matches
                    current_app.logger.info(f"Found match for page {page_idx} with score {best_score:.3f} to topic {best_match}")
                    match = Match(
                        project_id=project_id,
                        tree_id=topic_tree.id,
                        site_id=site.id,
                        page_index=page_idx,
                        matched_topics=[best_match],
                        similarity_scores=[best_score]
                    )
                    db.session.add(match)
                    total_matches += 1
        
        # Commit all changes
        db.session.commit()
        current_app.logger.info(f"Completed matching with {total_matches} total matches created")
        return True

@content_gaps_bp.route('/projects/<project_id>/compare/<tree_id>')
def compare_view(project_id, tree_id):
    # Get topic tree from database
    topic_tree = TopicTree.query.filter_by(id=tree_id, project_id=project_id).first()
    if not topic_tree:
        flash('Topic tree not found.')
        return redirect(url_for('content_gaps.view_project', project_id=project_id))

    # Get the most recent job for this tree to get selected sites
    job = ContentGapsJob.query.filter_by(
        project_id=project_id,
        tree_id=tree_id
    ).order_by(ContentGapsJob.created_at.desc()).first()
    
    selected_site_ids = []
    if job and job.selected_site_ids:
        selected_site_ids = job.selected_site_ids

    # Flatten topic tree
    def flatten_tree(nodes, parent_path=None):
        if parent_path is None:
            parent_path = []
        flat = []
        for idx, node in enumerate(nodes):
            path = parent_path + [str(idx)]
            flat.append({'path': path, 'name': node['name']})
            if 'children' in node and node['children']:
                flat.extend(flatten_tree(node['children'], path))
        return flat
    flat_topics = flatten_tree(topic_tree.tree_data)
    current_app.logger.info(f"Flattened tree into {len(flat_topics)} topics")

    # Get selected sites for this project
    if selected_site_ids:
        sites = Site.query.filter(Site.id.in_(selected_site_ids), Site.project_id == project_id).all()
    else:
        sites = Site.query.filter_by(project_id=project_id).all()
    site_map = {str(site.id): site for site in sites}  # Convert UUID to string for keys
    current_app.logger.info(f"Found {len(sites)} sites")
    current_app.logger.info(f"Site IDs: {list(site_map.keys())}")

    # Get all matches for this tree
    matches = Match.query.filter_by(project_id=project_id, tree_id=tree_id).all()
    current_app.logger.info(f"Found {len(matches)} matches")

    # Build topic->site->count mapping
    def path_key(path):
        return '-'.join(path)
    
    # Initialize counts and pages for all topics and sites
    topic_site_counts = {}
    topic_site_pages = {}
    
    # First, create entries for all topics and sites
    for topic in flat_topics:
        topic_key = path_key(topic['path'])
        topic_site_counts[topic_key] = {str(site.id): 0 for site in sites}  # Convert UUID to string
        topic_site_pages[topic_key] = {str(site.id): [] for site in sites}  # Convert UUID to string
    
    # Process matches
    for m in matches:
        site_id = str(m.site_id)  # Convert UUID to string
        page_index = m.page_index
        
        # Debug logging
        current_app.logger.info(f"Processing match for site {site_id} (type: {type(site_id)})")
        current_app.logger.info(f"Available site IDs: {list(topic_site_counts[list(topic_site_counts.keys())[0]].keys())}")
        
        if site_id not in site_map:
            current_app.logger.warning(f"Site ID {site_id} not found in site_map")
            continue
            
        for i, topic_path in enumerate(m.matched_topics):
            # Split the topic path into parts
            path_parts = topic_path.split('-')
            
            # Add the match to each level of the path
            current_path = []
            for part in path_parts:
                current_path.append(part)
                topic_key = '-'.join(current_path)
                
                if topic_key in topic_site_counts:
                    if site_id not in topic_site_counts[topic_key]:
                        current_app.logger.warning(f"Site ID {site_id} not found in topic_site_counts for topic {topic_key}")
                        continue
                        
                    topic_site_counts[topic_key][site_id] += 1
                    sim = m.similarity_scores[i] if i < len(m.similarity_scores) else None
                    topic_site_pages[topic_key][site_id].append({'page_index': page_index, 'similarity': sim})
                    current_app.logger.info(f"Added match to topic {topic_key} for site {site_id}")
                else:
                    current_app.logger.warning(f"Topic key {topic_key} not found in topic_site_counts")

    # Log final counts
    for topic_key, site_counts in topic_site_counts.items():
        for site_id, count in site_counts.items():
            if count > 0:
                current_app.logger.info(f"Topic {topic_key} has {count} matches for site {site_id}")

    return render_template(
        'compare.html',
        project_id=project_id,
        tree_id=tree_id,
        tree_name=topic_tree.tree_name,
        flat_topics=flat_topics,
        sites=sites,
        topic_site_counts=topic_site_counts,
        topic_site_pages=topic_site_pages,
    )

@content_gaps_bp.route('/projects/<project_id>/task-status')
def task_status(project_id):
    """Get the current status of the topic matching task"""
    try:
        # Get the most recent job for this project
        job = ContentGapsJob.query.filter_by(project_id=project_id).order_by(ContentGapsJob.created_at.desc()).first()
        
        if not job:
            return {'status': 'NOT_FOUND', 'error_message': 'No jobs found for this project'}, 404
        
        return {
            'status': job.status,
            'error_message': job.error_message,
            'compare_url': job.compare_url,
            'job_id': str(job.job_id),
            'jobs': [job.to_dict() for job in ContentGapsJob.query.filter_by(project_id=project_id).order_by(ContentGapsJob.created_at.desc()).all()]
        }
    except Exception as e:
        current_app.logger.error(f"Error getting task status: {e}")
        return {'status': 'ERROR', 'error_message': str(e)}, 500

@content_gaps_bp.route('/projects/<project_id>/delete-site', methods=['POST'])
def delete_site(project_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'error': 'Invalid request data'}), 400
            
        site_id = data.get('site_id')
        if not site_id:
            return jsonify({'status': 'error', 'error': 'No site specified'}), 400
        
        # Find the site and verify it belongs to the project
        site = Site.query.filter_by(id=site_id, project_id=project_id).first()
        if not site:
            return jsonify({'status': 'error', 'error': 'Site not found'}), 404
            
        # Delete the site - this will cascade delete related matches due to the foreign key constraint
        db.session.delete(site)
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting site: {str(e)}")
        return jsonify({'status': 'error', 'error': 'Failed to delete site'}), 500
