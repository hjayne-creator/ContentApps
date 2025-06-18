from flask import Flask
from markupsafe import Markup
from apps.content_plan.config import get_config
from extensions import csrf, db
import markdown
import json

def create_app():
    app = Flask(__name__, static_folder='apps/static')
    
    # Initialize CSRF protection
    csrf.init_app(app)
    
    # Load configuration
    config = get_config()
    app.config.from_object(config)
    config.init_app(app)
    
    # Initialize database
    db.init_app(app)
    
    # Register blueprints (sub-applications)
    from main.routes import main_bp
    from apps.content_plan.routes import init_app as init_content_plan
    from apps.content_gaps import init_app as init_content_gaps
    from apps.topic_competitors.routes import topic_competitors_bp
    from apps.content_briefs.routes import content_briefs_bp, format_reddit_summary
    
    app.register_blueprint(main_bp)
    app.register_blueprint(topic_competitors_bp, url_prefix='/apps/topic-competitors')
    app.register_blueprint(content_briefs_bp, url_prefix='/content-briefs')
    
    # Initialize content plan blueprint
    init_content_plan(app)
    
    # Initialize content gaps blueprint
    init_content_gaps(app)

    # Markdown filter for Jinja2
    @app.template_filter('markdown')
    def markdown_filter(text):
        return Markup(markdown.markdown(text or ""))
    
    # JSON filter for Jinja2
    @app.template_filter('from_json')
    def from_json_filter(text):
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    # Type filter for Jinja2
    @app.template_filter('type')
    def type_filter(value):
        return type(value).__name__
    
    app.jinja_env.filters['format_reddit_summary'] = format_reddit_summary
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)