from flask import Blueprint, render_template

topic_competitors_bp = Blueprint('topic_competitors', __name__,
                   template_folder='templates',
                   static_folder='static',
                   static_url_path='/apps/topic-competitors/static')

@topic_competitors_bp.route('/')
def index():
    return render_template('topic_competitors_home.html')
