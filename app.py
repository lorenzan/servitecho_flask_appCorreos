from flask import Flask, g, render_template
from config import Config
from extensions import db, login_manager
from models import Admin
import translations


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    translations.init_app(app)

    from public_routes import public_bp
    from admin_routes import admin_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return Admin.query.get(int(user_id))

    @app.errorhandler(404)
    def not_found(e):
        return render_template(
            "error.html",
            code=404,
            title="Page not found",
            message="Sorry, the page you're looking for doesn't exist or was moved.",
        ), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template(
            "error.html",
            code=500,
            title="Something went wrong",
            message="An unexpected error occurred. Please try again in a few minutes.",
        ), 500

    @app.before_request
    def _set_language():
        translations.set_language()

    @app.context_processor
    def inject_globals():
        from models import Service, ContentBlock, AdsSettings
        nav_services = Service.query.filter_by(active=True).order_by(Service.order).all()
        site_info = ContentBlock.query.filter_by(section_key="site_info").first()
        site_logo = ContentBlock.query.filter_by(section_key="logo").first()
        site_socials = ContentBlock.query.filter_by(section_key="socials").first()
        ads_settings = AdsSettings.query.first()
        if getattr(g, "lang", "es") == "en":
            nav_services = [translations.localize_service(s) for s in nav_services]
        return {
            "nav_services": nav_services,
            "site_info": site_info,
            "site_logo": site_logo,
            "site_socials": site_socials,
            "ads_settings": ads_settings,
            "current_lang": getattr(g, "lang", "es"),
            "t": translations.t,
        }

    with app.app_context():
        db.create_all()
        # Migración automática: agregar columna is_superadmin si falta (SQLite)
        try:
            db.session.execute(db.text("ALTER TABLE admins ADD COLUMN is_superadmin BOOLEAN DEFAULT 0"))
            db.session.commit()
        except Exception:
            pass
        # Migración: video opcional en servicios
        try:
            db.session.execute(db.text("ALTER TABLE services ADD COLUMN video_path VARCHAR(300)"))
            db.session.commit()
        except Exception:
            pass
        # Migración: reseñas destacadas (carrusel)
        try:
            db.session.execute(db.text("ALTER TABLE reviews ADD COLUMN featured BOOLEAN DEFAULT 0"))
            db.session.commit()
        except Exception:
            pass
        # Migrar imagen única del hero a la galería (una sola vez)
        try:
            from models import ContentBlock, HeroSlide, AboutSlide, QuoteGlassCard
            if HeroSlide.query.count() == 0:
                hero = ContentBlock.query.filter_by(section_key="hero").first()
                if hero and hero.image_path:
                    db.session.add(
                        HeroSlide(
                            image_path=hero.image_path,
                            caption="Standing Seam · Panel 5G · Modules",
                            sort_order=0,
                            active=True,
                        )
                    )
                    db.session.commit()
            if AboutSlide.query.count() == 0:
                about = ContentBlock.query.filter_by(section_key="about").first()
                if about and about.image_path:
                    db.session.add(
                        AboutSlide(
                            image_path=about.image_path,
                            sort_order=0,
                            active=True,
                        )
                    )
                    db.session.commit()
            # Create social media block if it doesn't exist
            if not ContentBlock.query.filter_by(section_key="socials").first():
                db.session.add(
                    ContentBlock(
                        section_key="socials",
                        label="Social Media (Footer)",
                        eyebrow="",  # WhatsApp URL optional
                        title="",  # Facebook URL
                        body="",  # Instagram URL
                        extra="",  # TikTok URL
                        image_path=None,
                    )
                )
                db.session.commit()
            # Quote block (editable glass cards)
            if not ContentBlock.query.filter_by(section_key="cotizacion").first():
                db.session.add(
                    ContentBlock(
                        section_key="cotizacion",
                        label="Quote (Glass Cards)",
                        eyebrow="Quote",
                        title="Tell us about your project",
                        body="Give us the location, describe what you need and upload site photos.",
                        extra="No obligation · Quick response",
                        image_path=None,
                    )
                )
                db.session.commit()
            # Reviews block (editable stacked cards)
            if not ContentBlock.query.filter_by(section_key="resenas").first():
                db.session.add(
                    ContentBlock(
                        section_key="resenas",
                        label="Reviews (Stacked Cards)",
                        eyebrow="Reviews",
                        title="Our customers' experience",
                        body="Completed projects, real opinions. Share yours too.",
                        extra="",
                        image_path=None,
                    )
                )
                db.session.commit()
        except Exception:
            db.session.rollback()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
