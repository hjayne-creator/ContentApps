from flask import Blueprint, render_template

app1_bp = Blueprint('app1', __name__,
                   template_folder='templates',
                   static_folder='static',
                   static_url_path='/app1/static')

@app1_bp.route('/')
def index():
    return render_template('app1_home.html')