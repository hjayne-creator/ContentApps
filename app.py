from flask import Flask

def create_app():
    app = Flask(__name__)
    
    # Register blueprints (sub-applications)
    from main.routes import main_bp
    from apps.content_plan.routes import content_plan_bp
    from apps.content_gaps.routes import content_gaps_bp
    from apps.topic_competitors.routes import topic_competitors_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(content_plan_bp, url_prefix='/apps/content-plan')
    app.register_blueprint(content_gaps_bp, url_prefix='/apps/content-gaps')
    app.register_blueprint(topic_competitors_bp, url_prefix='/apps/topic-competitors')
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)