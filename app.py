from flask import Flask, g, render_template, redirect, request, flash, url_for
from flask_wtf.csrf import CSRFError
from config import Config
from extensions import db, login_manager, csrf
from models import Admin
import translations


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    translations.init_app(app)

    from public_routes import public_bp
    from admin_routes import admin_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return Admin.query.get(int(user_id))

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        flash(
            "The form session expired or the request is invalid. Please try again.",
            "danger",
        )
        target = request.referrer
        if not target:
            target = (
                url_for("admin.login")
                if (request.path or "").startswith("/admin")
                else url_for("public.index")
            )
        return redirect(target)

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
        nav_services = list(
            Service.query.filter_by(active=True).order_by(Service.order).all()
        )
        site_info = ContentBlock.query.filter_by(section_key="site_info").first()
        site_logo = ContentBlock.query.filter_by(section_key="logo").first()
        site_socials = ContentBlock.query.filter_by(section_key="socials").first()
        ads_settings = AdsSettings.query.first()
        if getattr(g, "lang", "es") == "en":
            nav_services = [translations.localize_service(s) for s in nav_services]
        # Solo 3 productos en la barra; el resto va al desplegable "More"
        return {
            "nav_services": nav_services,
            "nav_services_visible": nav_services[:3],
            "nav_services_extra": nav_services[3:],
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
        # Migración: métodos de trabajo por servicio
        try:
            db.session.execute(db.text("ALTER TABLE services ADD COLUMN work_methods TEXT"))
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
            from models import ContentBlock, HeroSlide, AboutSlide, QuoteGlassCard, TrustCard
            # Admin CMS labels in English (visible in Site content panel)
            _block_labels_en = {
                "logo": "Logo",
                "hero": "Homepage (Hero)",
                "about": "About Us",
                "mission": "Mission",
                "vision": "Vision",
                "support": "24/7 Support",
                "why_us": "What Sets Us Apart",
                "site_info": "Contact Info (Header & Footer)",
                "socials": "Social Media (Footer)",
                "cotizacion": "Quote (Glass Cards)",
                "resenas": "Reviews (Stacked Cards)",
            }
            labels_changed = False
            for key, en_label in _block_labels_en.items():
                block = ContentBlock.query.filter_by(section_key=key).first()
                if block and block.label != en_label:
                    block.label = en_label
                    labels_changed = True
            if labels_changed:
                db.session.commit()

            # Seed default highlight cards (What sets us apart)
            if TrustCard.query.count() == 0:
                defaults = [
                    ("+30", "Years of Standing Seam warranty",
                     "Long-lasting protection with certified roof systems and real backing.", "shield"),
                    ("24/7", "Customer support",
                     "Continuous support for emergencies, maintenance and project follow-up.", "support"),
                    ("100%", "Professional installation",
                     "Specialized crews, flawless finishes and safety in every project.", "install"),
                    ("3", "Construction systems",
                     "Standing Seam, thermoacoustic panels and modules adapted to each project.", "systems"),
                ]
                for i, (metric, title, body, icon_key) in enumerate(defaults):
                    db.session.add(
                        TrustCard(
                            metric=metric,
                            title=title,
                            body=body,
                            icon_key=icon_key,
                            sort_order=i,
                            active=True,
                        )
                    )
                db.session.commit()

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
