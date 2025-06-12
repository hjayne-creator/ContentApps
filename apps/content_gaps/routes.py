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
from io import TextIOWrapper
load_dotenv()

# Use absolute path for projects directory
PROJECTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'projects'))
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
        if 'file' not in request.files:
            flash('No file uploaded')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
        
        if not file.filename.endswith('.csv'):
            flash('Please upload a CSV file')
            return redirect(request.url)
        
        try:
            csv_file = TextIOWrapper(file.stream, encoding='utf-8')
            reader = csv.DictReader(csv_file)
            pages = []
            for row in reader:
                if 'url' in row and 'title' in row and 'description' in row:
                    pages.append({
                        'url': row['url'],
                        'title': row['title'],
                        'description': row['description']
                    })
            
            if not pages:
                flash('No valid pages found in CSV')
                return redirect(request.url)
            
            # Create new site in database
            site = Site(
                id=str(uuid.uuid4()),
                project_id=project_id,
                label=file.filename.replace('.csv', ''),
                is_my_site=False,
                pages=pages
            )
            db.session.add(site)
            db.session.commit()
            
            flash('Site content uploaded successfully')
            return redirect(url_for('content_gaps.view_project', project_id=project_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error processing file: {e}')
            return redirect(request.url)
            
    return render_template('site_upload.html', project_id=project_id)

@content_gaps_bp.route('/projects/<project_id>/run-matching', methods=['POST'])
def run_topic_matching(project_id):
    topic_tree_id = request.form.get('topic_tree_id')
    if not topic_tree_id:
        flash('Topic tree ID is required.', 'error')
        return redirect(url_for('content_gaps.view_project', project_id=project_id))
        
    # Start the background task
    from .tasks import run_topic_matching_task
    task = run_topic_matching_task.delay(project_id, request.user.id if hasattr(request, 'user') else None, topic_tree_id)
    
    flash('Topic matching has started in the background. This may take several minutes to complete.', 'info')
    return redirect(url_for('content_gaps.view_project', project_id=project_id))

def _run_topic_matching_impl(project_id, user_id=None, topic_tree_id=None):
    if not topic_tree_id:
        raise ValueError("Topic tree ID is required")
        
    # Get topic tree from database
    topic_tree = TopicTree.query.filter_by(id=topic_tree_id, project_id=project_id).first()
    if not topic_tree:
        raise ValueError(f"Topic tree {topic_tree_id} not found")
    
    # Get all sites for this project
    sites = Site.query.filter_by(project_id=project_id).all()
    if not sites:
        raise ValueError('No site data found for this project.')

    # Flatten topic tree to (path, name) list
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

    # Use OpenAI Embeddings if available
    use_embeddings = bool(OPENAI_API_KEY)
    embedding_cache = {}
    def get_embedding(text):
        if text in embedding_cache:
            return embedding_cache[text]
        try:
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            resp = client.embeddings.create(
                model="text-embedding-3-large",
                input=text
            )
            emb = np.array(resp.data[0].embedding)
            embedding_cache[text] = emb
            return emb
        except Exception:
            return None

    def cosine_sim(a, b):
        if a is None or b is None:
            return 0.0
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    # Delete existing matches for this tree
    Match.query.filter_by(project_id=project_id, tree_id=topic_tree_id).delete()
    db.session.commit()

    # Matching
    threshold = 0.5 if use_embeddings else 0.2  # Lower threshold for keyword matching
    for site in sites:
        for idx, page in enumerate(site.pages):
            page_text = (page.get('title', '') + ' ' + page.get('description', '')).strip()
            matched_topics = []
            similarity_scores = []
            if use_embeddings:
                page_emb = get_embedding(page_text)
                for topic in flat_topics:
                    topic_emb = get_embedding(topic['name'])
                    sim = cosine_sim(page_emb, topic_emb)
                    if sim >= threshold:
                        matched_topics.append(topic['path'])
                        similarity_scores.append(float(sim))
            else:
                # Fallback: keyword overlap with more lenient matching
                page_words = set(page_text.lower().split())
                for topic in flat_topics:
                    topic_words = set(topic['name'].lower().split())
                    
                    # Calculate word overlap
                    common_words = page_words & topic_words
                    
                    # More lenient matching: if any significant words match
                    if len(common_words) > 0:
                        # Calculate similarity based on common words
                        overlap = len(common_words) / max(len(page_words), len(topic_words))
                        
                        # Special case for multi-word topics
                        if len(topic_words) > 1:
                            # If all topic words are found in the page, boost the score
                            if all(word in page_words for word in topic_words):
                                overlap = max(overlap, 0.5)
                        
                        if overlap >= threshold:
                            matched_topics.append(topic['path'])
                            similarity_scores.append(overlap)
            
            # Save match to database
            match = Match(
                project_id=project_id,
                tree_id=topic_tree_id,
                site_id=site.id,
                page_index=idx,
                matched_topics=matched_topics,
                similarity_scores=similarity_scores
            )
            db.session.add(match)
    
    try:
        db.session.commit()
        return {'status': 'success', 'tree_id': topic_tree_id}
    except Exception as e:
        db.session.rollback()
        raise ValueError(f'Error saving matches: {e}')

@content_gaps_bp.route('/projects/<project_id>/compare/<tree_id>')
def compare_view(project_id, tree_id):
    # Get topic tree from database
    topic_tree = TopicTree.query.filter_by(id=tree_id, project_id=project_id).first()
    if not topic_tree:
        flash('Topic tree not found.')
        return redirect(url_for('content_gaps.view_project', project_id=project_id))

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

    # Get all sites for this project
    sites = Site.query.filter_by(project_id=project_id).all()
    site_map = {site.id: site for site in sites}

    # Get all matches for this tree
    matches = Match.query.filter_by(project_id=project_id, tree_id=tree_id).all()

    # Build topic->site->count mapping
    def path_key(path):
        return '-'.join(path)
    topic_site_counts = {path_key(t['path']): {site.id: 0 for site in sites} for t in flat_topics}
    # For drilldown: topic->site->list of (page_index, similarity)
    topic_site_pages = {path_key(t['path']): {site.id: [] for site in sites} for t in flat_topics}

    for m in matches:
        site_id = m.site_id
        page_index = m.page_index
        for i, topic_path in enumerate(m.matched_topics):
            topic_key = path_key(topic_path)
            if topic_key in topic_site_counts:
                topic_site_counts[topic_key][site_id] += 1
                sim = m.similarity_scores[i] if i < len(m.similarity_scores) else None
                topic_site_pages[topic_key][site_id].append({'page_index': page_index, 'similarity': sim})

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
    project_dir = os.path.join(PROJECTS_DIR, project_id)
    settings_path = os.path.join(project_dir, 'settings.json')
    
    if not os.path.exists(settings_path):
        return {'status': 'NOT_FOUND', 'error_message': 'Project not found'}, 404
        
    try:
        with open(settings_path) as f:
            settings = json.load(f)
            
        jobs = settings.get('jobs', [])
        
        # Get the most recent job for current status
        current_job = jobs[-1] if jobs else None
        
        return {
            'status': current_job['status'] if current_job else 'UNKNOWN',
            'error_message': current_job.get('error_message') if current_job else None,
            'compare_url': current_job.get('compare_url') if current_job else None,
            'job_id': current_job['job_id'] if current_job else None,
            'jobs': jobs
        }
    except Exception as e:
        current_app.logger.error(f"Error getting task status: {e}")
        return {'status': 'ERROR', 'error_message': str(e)}, 500

@content_gaps_bp.route('/projects/<project_id>/delete-site', methods=['POST'])
def delete_site(project_id):
    site_id = request.form.get('site_id')
    if not site_id:
        flash('No site specified')
        return redirect(url_for('content_gaps.view_project', project_id=project_id))
    
    try:
        site = Site.query.filter_by(id=site_id, project_id=project_id).first_or_404()
        db.session.delete(site)
        db.session.commit()
        flash('Site deleted successfully')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting site: {e}')
    
    return redirect(url_for('content_gaps.view_project', project_id=project_id))
