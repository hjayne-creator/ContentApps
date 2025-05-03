from flask import Blueprint, render_template

content_gaps_bp = Blueprint('content_gaps', __name__,
                   template_folder='templates',
                   static_folder='static',
                   static_url_path='/apps/content-gaps/static')

@content_gaps_bp.route('/')
def index():
    return render_template('content_gaps_home.html')
