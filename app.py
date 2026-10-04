"""
Flask Application Factory
"""
from flask import Flask
from config import Config
from extensions import db, login_manager


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Extensions initialisieren
    db.init_app(app)
    login_manager.init_app(app)

    # Blueprints registrieren
    from blueprints.auth import auth_bp
    from blueprints.main import main_bp
    from blueprints.urlaub import urlaub_bp
    from blueprints.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(urlaub_bp)
    app.register_blueprint(admin_bp)

    # Jinja2 Globals
    from datetime import date
    @app.context_processor
    def inject_globals():
        return {'aktuelles_jahr': date.today().year}

    # 403/404 Fehlerseiten
    @app.errorhandler(403)
    def forbidden(e):
        from flask import render_template
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template('errors/404.html'), 404

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
