from flask import Blueprint, render_template

app2_bp = Blueprint('app2', __name__,
                   template_folder='templates',
                   static_folder='static',
                   static_url_path='/app2/static')

@app2_bp.route('/')
def index():
    return render_template('app2_home.html')