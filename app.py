from flask import Flask

from config import Config
from extensions import csrf, db, login_manager
from models import User


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    @app.after_request
    def prevent_stale_pages(response):
        """Never cache HTML: a cached page carries an expired CSRF token."""
        if response.mimetype == "text/html":
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.template_filter("money")
    def money_filter(value):
        if value is None:
            return "Not published"
        return "{:,.0f}".format(value)

    @app.context_processor
    def inject_globals():
        from datetime import datetime

        from models import Setting

        defaults = {
            "site_name": "UniGuide Uganda",
            "site_description": "",
            "contact_email": "",
            "contact_phone": "",
            "theme": "light",
            "accent_color": "#1B7F5A",
            "show_university_logos": "1",
            "sidebar_compact": "0",
            "date_format": "%d %B %Y",
        }
        try:
            settings = {key: Setting.get(key, value) for key, value in defaults.items()}
        except Exception:  # noqa: BLE001 - settings must never break page rendering
            settings = defaults
        import re

        accent = settings["accent_color"] or "#1B7F5A"
        if not re.match(r"^#[0-9A-Fa-f]{6}$", str(accent)):
            accent = "#1B7F5A"
        return {
            "site_name": settings["site_name"] or "UniGuide Uganda",
            "site_description": settings["site_description"],
            "contact_email": settings["contact_email"],
            "contact_phone": settings["contact_phone"],
            "site_theme": settings["theme"] if settings["theme"] in ("light", "dark") else "light",
            "accent_color": accent,
            "show_logos": str(settings["show_university_logos"]) in ("1", "true", "True", "on"),
            "sidebar_compact": str(settings["sidebar_compact"]) in ("1", "true", "True", "on"),
            "now": datetime.now().strftime(settings.get("date_format") or "%d %B %Y"),
        }

    from blueprints.main import main_bp
    from blueprints.auth import auth_bp
    from blueprints.student import student_bp
    from blueprints.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp)

    from seed import seed_all

    with app.app_context():
        seed_all()

    return app


def main():
    Application = create_app()
    Application.run(host="127.0.0.1", port=5000, debug=True)


if __name__ == "__main__":
    main()
