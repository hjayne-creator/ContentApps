from flask import Flask

def create_app():
    app = Flask(__name__)
    
    # Register blueprints (sub-applications)
    from main.routes import main_bp
    from app1.routes import app1_bp
    from app2.routes import app2_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(app1_bp, url_prefix='/app1')
    app.register_blueprint(app2_bp, url_prefix='/app2')
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)