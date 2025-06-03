from flask import Blueprint, render_template, request, redirect, url_for, flash
import os
import uuid
import json
import openai
import csv
from werkzeug.utils import secure_filename
import numpy as np

content_gaps_bp = Blueprint('content_gaps', __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/apps/content-gaps/static')

PROJECTS_DIR = os.path.join(os.path.dirname(__file__), 'projects')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o')

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
    if os.path.isfile(settings_path):
        with open(settings_path) as f:
            project = json.load(f)
    # Find all topic_tree_*.json files
    if os.path.isdir(project_dir):
        for fname in os.listdir(project_dir):
            if fname.startswith('topic_tree_') and fname.endswith('.json'):
                tree_path = os.path.join(project_dir, fname)
                try:
                    with open(tree_path) as tf:
                        tree_data = json.load(tf)
                    topic_trees.append({
                        'tree_id': tree_data.get('tree_id'),
                        'tree_name': tree_data.get('tree_name'),
                        'root_topic': tree_data.get('root_topic')
                    })
                except Exception:
                    continue
    return render_template('project_view.html', project_id=project_id, project=project, topic_trees=topic_trees)

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
    return render_template('topic_tree_edit.html', project_id=project_id, tree_id=tree_id, tree_data=tree_data)

@content_gaps_bp.route('/projects/<project_id>/sites/upload', methods=['GET', 'POST'])
def upload_site_content(project_id):
    project_dir = os.path.join(PROJECTS_DIR, project_id)
    if request.method == 'POST':
        site_label = request.form.get('site_label', '').strip()
        is_my_site = bool(request.form.get('is_my_site'))
        file = request.files.get('csv_file')
        if not site_label or not file:
            flash('Site label and CSV file are required.')
            return render_template('site_upload.html', project_id=project_id)
        filename = secure_filename(file.filename)
        try:
            os.makedirs(project_dir, exist_ok=True)
            # Parse CSV
            file.stream.seek(0)
            csv_reader = csv.DictReader((line.decode('utf-8') for line in file.stream), skipinitialspace=True)
            # Detect columns
            field_map = {'title': None, 'description': None, 'url': None}
            for field in csv_reader.fieldnames:
                fname = field.lower()
                if not field_map['title'] and ('title' in fname or 'page' in fname):
                    field_map['title'] = field
                if not field_map['description'] and (('description' in fname) or ('content' in fname) or ('meta' in fname)):
                    field_map['description'] = field
                if not field_map['url'] and ('url' in fname or 'link' in fname):
                    field_map['url'] = field
            if not field_map['title'] or not field_map['description'] or not field_map['url']:
                flash('CSV must include columns for title, description/content, and URL.')
                return render_template('site_upload.html', project_id=project_id)
            pages = []
            for row in csv_reader:
                pages.append({
                    'title': row.get(field_map['title'], ''),
                    'description': row.get(field_map['description'], ''),
                    'url': row.get(field_map['url'], '')
                })
            site_id = str(uuid.uuid4())
            site_data = {
                'site_id': site_id,
                'label': site_label,
                'is_my_site': is_my_site,
                'pages': pages
            }
            with open(os.path.join(project_dir, f'site_{site_id}.json'), 'w') as f:
                json.dump(site_data, f, indent=2)
            flash('Site content uploaded and parsed successfully.', 'success')
            return redirect(url_for('content_gaps.view_project', project_id=project_id))
        except Exception as e:
            flash(f'Error processing CSV: {e}')
            return render_template('site_upload.html', project_id=project_id)
    return render_template('site_upload.html', project_id=project_id)

@content_gaps_bp.route('/projects/<project_id>/run-matching', methods=['POST'])
def run_topic_matching(project_id):
    project_dir = os.path.join(PROJECTS_DIR, project_id)
    topic_tree_id = request.form.get('topic_tree_id')
    # Find topic tree (by ID if provided, else use first)
    topic_tree_files = [f for f in os.listdir(project_dir) if f.startswith('topic_tree_') and f.endswith('.json')]
    tree_path = None
    if topic_tree_id:
        for f in topic_tree_files:
            if topic_tree_id in f:
                tree_path = os.path.join(project_dir, f)
                break
    if not tree_path and topic_tree_files:
        tree_path = os.path.join(project_dir, topic_tree_files[0])
    if not tree_path:
        flash('No topic tree found for this project.')
        return redirect(url_for('content_gaps.view_project', project_id=project_id))
    try:
        with open(tree_path) as f:
            tree_data = json.load(f)
        topic_tree = tree_data.get('tree', [])
        tree_id = tree_data.get('tree_id')
    except Exception as e:
        flash(f'Error loading topic tree: {e}')
        return redirect(url_for('content_gaps.view_project', project_id=project_id))
    # Load all sites
    site_files = [f for f in os.listdir(project_dir) if f.startswith('site_') and f.endswith('.json')]
    sites = []
    for fname in site_files:
        try:
            with open(os.path.join(project_dir, fname)) as f:
                sites.append(json.load(f))
        except Exception:
            continue
    if not sites:
        flash('No site data found for this project.')
        return redirect(url_for('content_gaps.view_project', project_id=project_id))
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
                model="text-embedding-3-small",
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
    threshold = 0.75 if use_embeddings else 1
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
                # Fallback: keyword overlap
                page_words = set(page_text.lower().split())
                for topic in flat_topics:
                    topic_words = set(topic['name'].lower().split())
                    overlap = len(page_words & topic_words)
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
        flash('Topic matching complete.', 'success')
        return redirect(url_for('content_gaps.compare_view', project_id=project_id, tree_id=tree_id))
    except Exception as e:
        flash(f'Error saving matches: {e}')
        return redirect(url_for('content_gaps.view_project', project_id=project_id))

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
    topic_site_counts = {tuple(t['path']): {site['site_id']: 0 for site in sites} for t in flat_topics}
    # For drilldown: topic->site->list of (page_index, similarity)
    topic_site_pages = {tuple(t['path']): {site['site_id']: [] for site in sites} for t in flat_topics}
    for m in matches:
        site_id = m['site_id']
        page_index = m['page_index']
        for i, topic_path in enumerate(m['matched_topics']):
            topic_key = tuple(topic_path)
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
