from flask import Flask
from markupsafe import Markup
from apps.content_plan.config import get_config
from extensions import csrf
import markdown

def create_app():
    app = Flask(__name__, static_folder='apps/static')
    
    # Initialize CSRF protection
    csrf.init_app(app)
    
    # Load configuration
    config = get_config()
    app.config.from_object(config)
    config.init_app(app)
    
    # Register blueprints (sub-applications)
    from main.routes import main_bp
    from apps.content_plan.routes import content_plan_bp, init_app as init_content_plan
    from apps.content_gaps.routes import content_gaps_bp
    from apps.topic_competitors.routes import topic_competitors_bp
    from apps.content_briefs.routes import content_briefs_bp, format_reddit_summary
    
    app.register_blueprint(main_bp)
    app.register_blueprint(content_plan_bp, url_prefix='/apps/content-plan')
    app.register_blueprint(content_gaps_bp, url_prefix='/apps/content-gaps')
    app.register_blueprint(topic_competitors_bp, url_prefix='/apps/topic-competitors')
    app.register_blueprint(content_briefs_bp, url_prefix='/content-briefs')
    
    # Initialize content plan blueprint
    init_content_plan(app)

    # Markdown filter for Jinja2
    @app.template_filter('markdown')
    def markdown_filter(text):
        return Markup(markdown.markdown(text or ""))
    
    app.jinja_env.filters['format_reddit_summary'] = format_reddit_summary
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)