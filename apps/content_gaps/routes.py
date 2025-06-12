from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
import os
import uuid
import json
import openai
import csv
from werkzeug.utils import secure_filename
import numpy as np
from dotenv import load_dotenv
from .models import ContentGapsJob
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
    projects = []
    if os.path.exists(PROJECTS_DIR):
        for project_id in os.listdir(PROJECTS_DIR):
            project_dir = os.path.join(PROJECTS_DIR, project_id)
            settings_path = os.path.join(project_dir, 'settings.json')
            if os.path.isdir(project_dir) and os.path.isfile(settings_path):
                try:
                    with open(settings_path) as f:
                        settings = json.load(f)
                    projects.append({
                        'project_id': settings.get('project_id', project_id),
                        'project_name': settings.get('project_name', 'Untitled'),
                        'primary_url': settings.get('primary_url', ''),
                        'is_my_site': settings.get('is_my_site', False)
                    })
                except Exception:
                    continue
    return render_template('content_gaps_index.html', projects=projects)

@content_gaps_bp.route('/projects/new', methods=['GET', 'POST'])
def create_project():
    if request.method == 'POST':
        project_name = request.form.get('project_name', '').strip()
        primary_url = request.form.get('primary_url', '').strip()
        is_my_site = bool(request.form.get('is_my_site'))
        if not project_name or not primary_url:
            flash('Project name and primary website URL are required.')
            return render_template('project_new.html')
        project_id = str(uuid.uuid4())
        project_dir = os.path.join(PROJECTS_DIR, project_id)
        try:
            os.makedirs(project_dir, exist_ok=True)
            settings = {
                'project_id': project_id,
                'project_name': project_name,
                'primary_url': primary_url,
                'is_my_site': is_my_site
            }
            with open(os.path.join(project_dir, 'settings.json'), 'w') as f:
                json.dump(settings, f, indent=2)
            return redirect(url_for('content_gaps.view_project', project_id=project_id))
        except Exception as e:
            flash(f'Error creating project: {e}')
            return render_template('project_new.html')
    return render_template('project_new.html')

@content_gaps_bp.route('/projects/<project_id>')
def view_project(project_id):
    project_dir = os.path.join(PROJECTS_DIR, project_id)
    settings_path = os.path.join(project_dir, 'settings.json')
    project = None
    topic_trees = []
    sites = []
    
    # Load project settings with error handling
    if os.path.isfile(settings_path):
        try:
            with open(settings_path) as f:
                content = f.read().strip()
                if content:  # Only try to parse if file has content
                    project = json.loads(content)
                else:
                    project = {'project_id': project_id, 'project_name': 'Untitled Project'}
        except json.JSONDecodeError:
            # If JSON is invalid, create a basic project object
            project = {'project_id': project_id, 'project_name': 'Untitled Project'}
        except Exception as e:
            flash(f'Error loading project settings: {str(e)}', 'error')
            project = {'project_id': project_id, 'project_name': 'Untitled Project'}
    
    # Get job statuses from database
    jobs = ContentGapsJob.query.filter_by(project_id=project_id).order_by(ContentGapsJob.created_at.desc()).limit(10).all()
    job_statuses = [job.to_dict() for job in jobs]
    
    # Find all topic_tree_*.json files
    if os.path.isdir(project_dir):
        for fname in os.listdir(project_dir):
            if fname.startswith('topic_tree_') and fname.endswith('.json'):
                tree_path = os.path.join(project_dir, fname)
                try:
                    with open(tree_path) as tf:
                        tree_data = json.load(tf)
                    tree_id = tree_data.get('tree_id')
                    # Check if a report exists for this tree
                    has_report = os.path.exists(os.path.join(project_dir, f'matches_{tree_id}.json'))
                    topic_trees.append({
                        'tree_id': tree_id,
                        'tree_name': tree_data.get('tree_name'),
                        'root_topic': tree_data.get('root_topic'),
                        'has_report': has_report
                    })
                except Exception:
                    continue
            elif fname.startswith('site_') and fname.endswith('.json'):
                site_path = os.path.join(project_dir, fname)
                try:
                    with open(site_path) as sf:
                        site_data = json.load(sf)
                    sites.append({
                        'site_id': site_data.get('site_id'),
                        'label': site_data.get('label', 'Untitled Site'),
                        'is_my_site': site_data.get('is_my_site', False),
                        'pages': site_data.get('pages', [])
                    })
                except Exception:
                    continue
    return render_template('project_view.html', project_id=project_id, project=project, topic_trees=topic_trees, sites=sites, jobs=job_statuses)

@content_gaps_bp.route('/projects/<project_id>/topic-trees/new', methods=['GET', 'POST'])
def create_topic_tree(project_id):
    project_dir = os.path.join(PROJECTS_DIR, project_id)
    if request.method == 'POST':
        tree_name = request.form.get('tree_name', '').strip()
        root_topic = request.form.get('root_topic', '').strip()
        if not tree_name or not root_topic:
            flash('Tree name and root topic are required.')
            return render_template('topic_tree_new.html', project_id=project_id)
        tree_id = str(uuid.uuid4())
        tree, error = generate_topic_tree_llm(root_topic)
        if error:
            flash(error)
            tree = []
        tree_data = {
            'tree_id': tree_id,
            'tree_name': tree_name,
            'root_topic': root_topic,
            'tree': tree
        }
        try:
            os.makedirs(project_dir, exist_ok=True)
            tree_path = os.path.join(project_dir, f'topic_tree_{tree_id}.json')
            with open(tree_path, 'w') as f:
                json.dump(tree_data, f, indent=2)
            return redirect(url_for('content_gaps.edit_topic_tree', project_id=project_id, tree_id=tree_id))
        except Exception as e:
            flash(f'Error creating topic tree: {e}')
            return render_template('topic_tree_new.html', project_id=project_id)
    return render_template('topic_tree_new.html', project_id=project_id)

@content_gaps_bp.route('/projects/<project_id>/topic-trees/<tree_id>/edit', methods=['GET', 'POST'])
def edit_topic_tree(project_id, tree_id):
    project_dir = os.path.join(PROJECTS_DIR, project_id)
    tree_path = os.path.join(project_dir, f'topic_tree_{tree_id}.json')
    tree_data = {'tree_name': '', 'root_topic': '', 'tree': []}
    if request.method == 'POST':
        tree_json = request.form.get('tree_json', '')
        try:
            new_tree = json.loads(tree_json)
            # Load existing data
            if os.path.isfile(tree_path):
                with open(tree_path) as f:
                    tree_data = json.load(f)
            tree_data['tree'] = new_tree
            with open(tree_path, 'w') as f:
                json.dump(tree_data, f, indent=2)
            flash('Tree saved successfully.', 'success')
        except Exception as e:
            flash(f'Error saving tree: {e}')
    # Always reload for display
    if os.path.isfile(tree_path):
        try:
            with open(tree_path) as f:
                tree_data = json.load(f)
        except Exception:
            flash('Could not load topic tree data.')
    else:
        flash('Topic tree not found.')
    return render_template('topic_tree_edit_v.html', project_id=project_id, tree_id=tree_id, tree_data=tree_data)

@content_gaps_bp.route('/projects/<project_id>/topic-trees/<tree_id>/edit-vertical', methods=['GET', 'POST'])
def edit_topic_tree_vertical(project_id, tree_id):
    project_dir = os.path.join(PROJECTS_DIR, project_id)
    tree_path = os.path.join(project_dir, f'topic_tree_{tree_id}.json')
    tree_data = {'tree_name': '', 'root_topic': '', 'tree': []}
    if request.method == 'POST':
        tree_json = request.form.get('tree_json', '')
        try:
            new_tree = json.loads(tree_json)
            # Load existing data
            if os.path.isfile(tree_path):
                with open(tree_path) as f:
                    tree_data = json.load(f)
            tree_data['tree'] = new_tree
            with open(tree_path, 'w') as f:
                json.dump(tree_data, f, indent=2)
            flash('Tree saved successfully.', 'success')
        except Exception as e:
            flash(f'Error saving tree: {e}')
    # Always reload for display
    if os.path.isfile(tree_path):
        try:
            with open(tree_path) as f:
                tree_data = json.load(f)
        except Exception:
            flash('Could not load topic tree data.')
    else:
        flash('Topic tree not found.')
    return render_template('topic_tree_edit_v.html', project_id=project_id, tree_id=tree_id, tree_data=tree_data)

@content_gaps_bp.route('/projects/<project_id>/sites/upload', methods=['GET', 'POST'])
def upload_site_content(project_id):
    project_dir = os.path.join(PROJECTS_DIR, project_id)
    preview_data = None
    field_map = None
    sample_rows = None
    mapping_required = False
    csv_columns = []
    mapping_sample_rows = []
    if request.method == 'POST':
        # Step 1: Confirm and save
        if request.form.get('confirm') == '1':
            site_label = request.form.get('site_label', '').strip()
            is_my_site = request.form.get('is_my_site') == 'on'
            try:
                pages_json = request.form.get('pages_json')
                field_map_json = request.form.get('field_map_json')
                if not pages_json or not field_map_json:
                    flash('Missing preview data. Please re-upload the CSV.', 'error')
                    return render_template('site_upload.html', project_id=project_id)
                pages = json.loads(pages_json)
                field_map = json.loads(field_map_json)
                site_id = str(uuid.uuid4())
                site_data = {
                    'site_id': site_id,
                    'label': site_label,
                    'is_my_site': is_my_site,
                    'pages': pages
                }
                os.makedirs(project_dir, exist_ok=True)
                with open(os.path.join(project_dir, f'site_{site_id}.json'), 'w') as f:
                    json.dump(site_data, f, indent=2)
                flash('Site content uploaded and parsed successfully.', 'success')
                return redirect(url_for('content_gaps.view_project', project_id=project_id))
            except Exception as e:
                flash(f'Error saving site: {e}', 'error')
                return render_template('site_upload.html', project_id=project_id)
        # Step 2: Mapping form submit
        elif request.form.get('mapping_confirm') == '1':
            site_label = request.form.get('site_label', '').strip()
            is_my_site = request.form.get('is_my_site') == 'on'
            # Get mapping from form
            title_col = request.form.get('title_column')
            desc_col = request.form.get('description_column')
            url_col = request.form.get('url_column')
            # Get CSV columns and file from hidden fields
            csv_columns = request.form.getlist('csv_columns')
            # The file is re-uploaded
            file = request.files.get('csv_file')
            if not site_label or not file or not title_col or not desc_col or not url_col:
                flash('All fields and mapping are required.', 'error')
                return render_template('site_upload.html', project_id=project_id)
            try:
                file.stream.seek(0)
                csv_reader = csv.DictReader((line.decode('utf-8') for line in file.stream), skipinitialspace=True)
                pages = []
                for row in csv_reader:
                    title = row.get(title_col, '').strip()
                    if not title:  # Skip rows with empty titles
                        continue
                    pages.append({
                        'title': title,
                        'description': row.get(desc_col, ''),
                        'url': row.get(url_col, '')
                    })
                sample_rows = pages[:5]
                field_map = {'title': title_col, 'description': desc_col, 'url': url_col}
                preview_data = {
                    'site_label': site_label,
                    'is_my_site': is_my_site,
                    'field_map': field_map,
                    'sample_rows': sample_rows,
                    'pages_json': pages,
                    'field_map_json': field_map
                }
                flash('Preview your mapped columns and sample rows below. Click Confirm to save.', 'info')
                return render_template('site_upload.html', project_id=project_id, preview_data=preview_data)
            except Exception as e:
                flash(f'Error processing CSV with mapping: {e}', 'error')
                return render_template('site_upload.html', project_id=project_id)
        # Step 3: Initial upload, try auto-detect
        site_label = request.form.get('site_label', '').strip()
        is_my_site = request.form.get('is_my_site') == 'on'
        file = request.files.get('csv_file')
        if not site_label or not file:
            flash('Site label and CSV file are required.', 'error')
            return render_template('site_upload.html', project_id=project_id)
        try:
            file.stream.seek(0)
            csv_reader = csv.DictReader((line.decode('utf-8') for line in file.stream), skipinitialspace=True)
            csv_columns = csv_reader.fieldnames or []
            # Auto-detect columns
            field_map = {'title': None, 'description': None, 'url': None}
            for field in csv_columns:
                fname = field.lower()
                if not field_map['title'] and ('title' in fname or 'page' in fname):
                    field_map['title'] = field
                if not field_map['description'] and (('description' in fname) or ('meta' in fname)):
                    field_map['description'] = field
                if not field_map['url'] and ('address' in fname or 'url' in fname or 'link' in fname):
                    field_map['url'] = field
            if not field_map['title'] or not field_map['description'] or not field_map['url']:
                # Show mapping UI
                mapping_required = True
                # Get sample rows for mapping preview
                file.stream.seek(0)
                csv_reader = csv.DictReader((line.decode('utf-8') for line in file.stream), skipinitialspace=True)
                mapping_sample_rows = []
                for i, row in enumerate(csv_reader):
                    if i >= 5:
                        break
                    mapping_sample_rows.append(row)
                flash('Could not auto-detect all required columns. Please map the fields below.', 'error')
                return render_template('site_upload.html', project_id=project_id, mapping_required=True, csv_columns=csv_columns, mapping_sample_rows=mapping_sample_rows, site_label=site_label, is_my_site=is_my_site)
            # If auto-detect succeeded, parse as before
            pages = []
            for row in csv_reader:
                title = row.get(field_map['title'], '').strip()
                if not title:  # Skip rows with empty titles
                    continue
                pages.append({
                    'title': title,
                    'description': row.get(field_map['description'], ''),
                    'url': row.get(field_map['url'], '')
                })
            sample_rows = pages[:5]
            preview_data = {
                'site_label': site_label,
                'is_my_site': is_my_site,
                'field_map': field_map,
                'sample_rows': sample_rows,
                'pages_json': pages,
                'field_map_json': field_map
            }
            flash('Preview detected columns and sample rows below. Click Confirm to save.', 'info')
            return render_template('site_upload.html', project_id=project_id, preview_data=preview_data)
        except Exception as e:
            flash(f'Error processing CSV: {e}', 'error')
            return render_template('site_upload.html', project_id=project_id)
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
    # Use absolute path for project directory
    project_dir = os.path.abspath(os.path.join(PROJECTS_DIR, project_id))
    if not topic_tree_id:
        raise ValueError("Topic tree ID is required")
        
    # Find topic tree
    tree_path = os.path.join(project_dir, f'topic_tree_{topic_tree_id}.json')
    print(f"Looking for topic tree at: {tree_path}")
    print(f"Directory contents: {os.listdir(project_dir) if os.path.exists(project_dir) else 'Directory not found'}")
    print(f"File exists: {os.path.exists(tree_path)}")
    print(f"File permissions: {oct(os.stat(tree_path).st_mode)[-3:] if os.path.exists(tree_path) else 'N/A'}")
    
    if not os.path.exists(tree_path):
        raise ValueError(f"Topic tree {topic_tree_id} not found")
        
    try:
        with open(tree_path) as f:
            tree_data = json.load(f)
        topic_tree = tree_data.get('tree', [])
        tree_id = tree_data.get('tree_id')
    except Exception as e:
        print(f"Error loading topic tree: {str(e)}")
        raise ValueError(f'Error loading topic tree: {e}')

    # Load all sites
    site_files = [f for f in os.listdir(project_dir) if f.startswith('site_') and f.endswith('.json')]
    sites = []
    for fname in site_files:
        try:
            with open(os.path.join(project_dir, fname)) as f:
                site = json.load(f)
                # Defensive: if pages is a string, parse it
                if isinstance(site.get('pages'), str):
                    try:
                        site['pages'] = json.loads(site['pages'])
                    except Exception:
                        site['pages'] = []
                sites.append(site)
        except Exception:
            continue
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
    flat_topics = flatten_tree(topic_tree)

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

    # Matching
    matches = []
    threshold = 0.5 if use_embeddings else 0.2  # Lower threshold for keyword matching
    for site in sites:
        site_id = site['site_id']
        for idx, page in enumerate(site['pages']):
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
            
            matches.append({
                'site_id': site_id,
                'page_index': idx,
                'matched_topics': matched_topics,
                'similarity_scores': similarity_scores
            })

    # Save results
    try:
        with open(os.path.join(project_dir, f'matches_{tree_id}.json'), 'w') as f:
            json.dump(matches, f, indent=2)
        return {'status': 'success', 'matches_file': f'matches_{tree_id}.json'}
    except Exception as e:
        raise ValueError(f'Error saving matches: {e}')

@content_gaps_bp.route('/projects/<project_id>/compare/<tree_id>')
def compare_view(project_id, tree_id):
    project_dir = os.path.join(PROJECTS_DIR, project_id)
    # Load topic tree
    tree_path = os.path.join(project_dir, f'topic_tree_{tree_id}.json')
    topic_tree = []
    tree_name = ''
    if os.path.isfile(tree_path):
        with open(tree_path) as f:
            tree_data = json.load(f)
            topic_tree = tree_data.get('tree', [])
            tree_name = tree_data.get('tree_name', '')
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
    flat_topics = flatten_tree(topic_tree)
    # Load sites
    site_files = [f for f in os.listdir(project_dir) if f.startswith('site_') and f.endswith('.json')]
    sites = []
    site_map = {}
    for fname in site_files:
        with open(os.path.join(project_dir, fname)) as f:
            site = json.load(f)
            sites.append(site)
            site_map[site['site_id']] = site
    # Load matches
    matches_path = os.path.join(project_dir, f'matches_{tree_id}.json')
    matches = []
    if os.path.isfile(matches_path):
        with open(matches_path) as f:
            matches = json.load(f)
    # Build topic->site->count mapping
    def path_key(path):
        return '-'.join(path)
    topic_site_counts = {path_key(t['path']): {site['site_id']: 0 for site in sites} for t in flat_topics}
    # For drilldown: topic->site->list of (page_index, similarity)
    topic_site_pages = {path_key(t['path']): {site['site_id']: [] for site in sites} for t in flat_topics}
    for m in matches:
        site_id = m['site_id']
        page_index = m['page_index']
        for i, topic_path in enumerate(m['matched_topics']):
            topic_key = path_key(topic_path)
            if topic_key in topic_site_counts:
                topic_site_counts[topic_key][site_id] += 1
                sim = m['similarity_scores'][i] if i < len(m['similarity_scores']) else None
                topic_site_pages[topic_key][site_id].append({'page_index': page_index, 'similarity': sim})
    return render_template(
        'compare.html',
        project_id=project_id,
        tree_id=tree_id,
        tree_name=tree_name,
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
    try:
        data = request.get_json()
        site_id = data.get('site_id')
        if not site_id:
            return {'error': 'Site ID is required'}, 400
            
        project_dir = os.path.join(PROJECTS_DIR, project_id)
        site_path = os.path.join(project_dir, f'site_{site_id}.json')
        
        if os.path.exists(site_path):
            os.remove(site_path)
            return {'status': 'success'}, 200
        else:
            return {'error': 'Site not found'}, 404
            
    except Exception as e:
        return {'error': str(e)}, 500
