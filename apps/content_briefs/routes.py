from flask import Blueprint, render_template, request, jsonify, send_file, abort, current_app
import os
import json
import io
from apps.content_briefs.config import Config
from extensions import csrf
from apps.content_briefs.tasks.generate_brief import generate_brief_task
try:
    from docx import Document
except ImportError:
    Document = None

content_briefs_bp = Blueprint(
    'content_briefs_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

BRIEFS_DIR = Config.BRIEFS_DIR

@content_briefs_bp.route('/', methods=['GET'])
def index():
    return render_template('briefs_index.html')

@content_briefs_bp.route('/start', methods=['POST'])
def start_brief():
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form
    keyword = data.get('keyword')
    website = data.get('website')
    if not keyword or not website:
        return jsonify({'error': 'Missing keyword or website'}), 400
    task = generate_brief_task.apply_async(args=[keyword, website])
    return jsonify({'task_id': task.id}), 202

@content_briefs_bp.route('/download/<task_id>')
def download_brief(task_id):
    path = os.path.join(BRIEFS_DIR, f'brief_{task_id}.json')
    try:
        return send_file(path, as_attachment=True)
    except FileNotFoundError:
        abort(404)

@content_briefs_bp.route('/download_docx/<task_id>')
def download_docx(task_id):
    if Document is None:
        return "python-docx is not installed.", 500
    path = os.path.join(BRIEFS_DIR, f'brief_{task_id}.json')
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        brief = data.get('brief', {})
        doc = Document()
        if brief.get('title'):
            doc.add_heading(brief['title'], 0)
        if brief.get('introduction'):
            doc.add_paragraph('Introduction: ' + brief['introduction'])
        if brief.get('audience'):
            doc.add_paragraph('Audience: ' + brief['audience'])
        if brief.get('search_intent'):
            doc.add_paragraph('Search Intent: ' + brief['search_intent'])
        if brief.get('talking_points'):
            doc.add_paragraph('Main Talking Points:')
            for tp in brief['talking_points']:
                doc.add_paragraph(tp, style='List Bullet')
        if brief.get('word_count'):
            doc.add_paragraph('Suggested Word Count: ' + str(brief['word_count']))
        if brief.get('full_brief'):
            doc.add_paragraph(brief['full_brief'])
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        return send_file(buf, as_attachment=True, download_name='blog_brief.docx', mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    except Exception as e:
        print(f"DOCX download error: {e}")
        return "Brief not found or could not generate DOCX.", 404

@content_briefs_bp.route('/results/<task_id>')
def results_page(task_id):
    path = os.path.join(BRIEFS_DIR, f'brief_{task_id}.json')
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        brief = data.get('brief', {})
        full_brief = brief.get('full_brief', 'No brief found.')
        keyword = data.get('keyword', '')
        keyword_info = data.get('keyword_info', '')
        keywords = [keyword] if keyword else []
        reddit_summaries = data.get('reddit_summaries', {})
        serp_data = data.get('serp_data', {})
        related_keywords = data.get('related_keywords', [])
        brand_brief = data.get('website_summary', '')
        return render_template('results.html', full_brief=full_brief, brief=brief, task_id=task_id, keywords=keywords, reddit_summaries=reddit_summaries, serp_data=serp_data, keyword_info=keyword_info, related_keywords=related_keywords, brand_brief=brand_brief)
    except Exception as e:
        return f"Error loading brief: {e}", 404

@content_briefs_bp.route('/admin')
def admin_page():
    briefs = []
    try:
        for fname in os.listdir(BRIEFS_DIR):
            if fname.endswith('.json'):
                task_id = fname.replace('brief_', '').replace('.json', '')
                path = os.path.join(BRIEFS_DIR, fname)
                with open(path, 'r') as f:
                    data = json.load(f)
                keywords = data.get('keywords', [])
                topic = keywords[0] if keywords else 'Untitled'
                briefs.append({
                    'task_id': task_id,
                    'topic': topic,
                    'json_link': f'/content-briefs/download/{task_id}',
                    'docx_link': f'/content-briefs/download_docx/{task_id}',
                    'results_link': f'/content-briefs/results/{task_id}'
                })
    except Exception as e:
        return f"Error loading briefs: {e}", 500
    return render_template('admin.html', briefs=briefs)


@content_briefs_bp.route('/progress/<task_id>')
def task_progress(task_id):
    task = generate_brief_task.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {'state': task.state, 'progress': 0, 'message': 'Task pending...'}
    elif task.state == 'PROGRESS':
        response = {'state': task.state, 'progress': task.info.get('step', 0), 'message': task.info.get('message', '')}
    elif task.state == 'SUCCESS':
        response = {'state': task.state, 'result': task.result.get('result', '')}
    else:
        response = {'state': task.state, 'message': str(task.info)}
    return jsonify(response)

def format_reddit_summary(text):
    import re
    if not text:
        return ''
    lines = re.split(r'(?<=\n)', text)
    items = []
    buffer = ''
    for line in lines:
        m = re.match(r'\s*(\d+)\.\s+(.*)', line)
        if m:
            if buffer:
                items.append({'type': 'p', 'text': buffer.strip()})
                buffer = ''
            items.append({'type': 'li', 'text': m.group(2).strip()})
        else:
            buffer += line
    if buffer.strip():
        items.append({'type': 'p', 'text': buffer.strip()})
    html = ''
    li_items = [i['text'] for i in items if i['type'] == 'li']
    if li_items:
        html += '<ol>' + ''.join(f'<li>{x}</li>' for x in li_items) + '</ol>'
    for i in items:
        if i['type'] == 'p' and i['text']:
            html += f'<p>{i["text"]}</p>'
    return html 

@content_briefs_bp.route('/test-form', methods=['GET', 'POST'])
def test_form():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
        keyword = data.get('keyword')
        website = data.get('website')
    return render_template('test_form.html') 