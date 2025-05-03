from flask import Blueprint, render_template

content_plan_bp = Blueprint('content_plan', __name__,
                   template_folder='templates',
                   static_folder='static',
                   static_url_path='/apps/content-plan/static')

@content_plan_bp.route('/')
def index():
    return render_template('content_plan_home.html')
