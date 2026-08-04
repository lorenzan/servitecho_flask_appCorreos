from flask import Flask
from config import Config
from extensions import db, login_manager
from models import Admin


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    from public_routes import public_bp
    from admin_routes import admin_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return Admin.query.get(int(user_id))

    @app.context_processor
    def inject_globals():
        from models import Service, ContentBlock
        nav_services = Service.query.filter_by(active=True).order_by(Service.order).all()
        site_info = ContentBlock.query.filter_by(section_key="site_info").first()
        site_logo = ContentBlock.query.filter_by(section_key="logo").first()
        return {"nav_services": nav_services, "site_info": site_info, "site_logo": site_logo}

    with app.app_context():
        db.create_all()
        # Migración automática: agregar columna is_superadmin si falta (SQLite)
        try:
            db.session.execute(db.text("ALTER TABLE admins ADD COLUMN is_superadmin BOOLEAN DEFAULT 0"))
            db.session.commit()
        except Exception:
            pass

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
