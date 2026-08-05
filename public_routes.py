from flask import Blueprint, current_app, g, render_template, request, redirect, url_for, flash, Response
from sqlalchemy import desc

from extensions import db
from models import ContentBlock, Service, Review, Quote, QuoteImage
from utils import save_upload
from utils_email import notify_new_review, notify_new_quote
import translations

public_bp = Blueprint("public", __name__)


@public_bp.route("/lang/<lang>")
def set_lang(lang):
    """Cambia el idioma del visitante y guarda la preferencia en una cookie."""
    lang = lang if lang in ("es", "en") else "es"
    # Solo redirigimos a la página desde la que vino si es de nuestro sitio
    # (evita redirección abierta vía Referer).
    referrer = request.referrer or ""
    target = referrer if request.host in referrer else url_for("public.index")
    resp = redirect(target)
    resp.set_cookie("lang", lang, max_age=60 * 60 * 24 * 365, samesite="Lax")
    return resp


def get_blocks(*keys):
    """Fetch several content blocks at once as a dict keyed by section_key."""
    blocks = ContentBlock.query.filter(ContentBlock.section_key.in_(keys)).all()
    return {b.section_key: b for b in blocks}


@public_bp.route("/")
def index():
    blocks = get_blocks(
        "hero", "about", "mission", "vision", "values", "support", "why_us"
    )
    services = Service.query.filter_by(active=True).order_by(Service.order).all()
    reviews = (
        Review.query.filter_by(approved=True)
        .order_by(desc(Review.created_at))
        .limit(6)
        .all()
    )
    if getattr(g, "lang", "es") == "en":
        blocks = {k: translations.localize_block(b) for k, b in blocks.items()}
        services = [translations.localize_service(s) for s in services]
        reviews = [translations.localize_review(r) for r in reviews]
    return render_template(
        "index.html", blocks=blocks, services=services, reviews=reviews
    )


@public_bp.route("/servicios/<slug>")
def servicio_detalle(slug):
    servicio = Service.query.filter_by(slug=slug, active=True).first_or_404()
    otros = (
        Service.query.filter(Service.slug != slug, Service.active == True)
        .order_by(Service.order)
        .all()
    )
    if getattr(g, "lang", "es") == "en":
        servicio = translations.localize_service(servicio)
        otros = [translations.localize_service(o) for o in otros]
    return render_template("servicio_detalle.html", servicio=servicio, otros=otros)


@public_bp.route("/resenas", methods=["GET", "POST"])
def resenas():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        rating = request.form.get("rating", "5")
        comment = request.form.get("comment", "").strip()

        errors = []
        if not name:
            errors.append("El nombre es obligatorio.")
        if not comment:
            errors.append("El comentario es obligatorio.")
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError
        except ValueError:
            errors.append("La calificación debe ser entre 1 y 5.")

        if errors:
            for e in errors:
                flash(e, "danger")
        else:
            review = Review(name=name, email=email, rating=rating, comment=comment)
            db.session.add(review)
            db.session.commit()
            notify_new_review(review)
            flash("¡Gracias por tu reseña! Ya fue publicada en el sitio.", "success")
            return redirect(url_for("public.resenas"))

    reviews = (
        Review.query.filter_by(approved=True)
        .order_by(desc(Review.created_at))
        .all()
    )
    if getattr(g, "lang", "es") == "en":
        reviews = [translations.localize_review(r) for r in reviews]
    return render_template("resenas.html", reviews=reviews)


@public_bp.route("/cotizacion", methods=["GET", "POST"])
def cotizacion():
    services = Service.query.filter_by(active=True).order_by(Service.order).all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        location = request.form.get("location", "").strip()
        latitude = request.form.get("latitude", "").strip()
        longitude = request.form.get("longitude", "").strip()
        service_type = request.form.get("service_type", "").strip()
        description = request.form.get("description", "").strip()

        errors = []
        if not name:
            errors.append("El nombre es obligatorio.")
        if not phone:
            errors.append("El teléfono es obligatorio.")
        if not location:
            errors.append("La ubicación es obligatoria.")
        if not description:
            errors.append("Por favor describe lo que necesitas.")

        if errors:
            for e in errors:
                flash(e, "danger")
        else:
            quote = Quote(
                name=name,
                phone=phone,
                email=email,
                location=location,
                latitude=float(latitude) if latitude else None,
                longitude=float(longitude) if longitude else None,
                service_type=service_type,
                description=description,
            )
            db.session.add(quote)
            db.session.flush()  # get quote.id before commit

            files = request.files.getlist("images")
            for f in files[:6]:  # cap at 6 images
                rel_path = save_upload(f, "quotes")
                if rel_path:
                    db.session.add(QuoteImage(quote_id=quote.id, image_path=rel_path))

            db.session.commit()
            notify_new_quote(quote)
            return redirect(url_for("public.cotizacion_gracias"))

    if getattr(g, "lang", "es") == "en":
        services = [translations.localize_service(s) for s in services]
    return render_template("cotizacion.html", services=services)


@public_bp.route("/cotizacion/gracias")
def cotizacion_gracias():
    return render_template("cotizacion_gracias.html")


# ---------- SEO: robots.txt y sitemap.xml ----------

def _site_base_url():
    """Dominio público para enlaces absolutos (SITE_URL si está configurado,
    si no el Host de la petición)."""
    configured = current_app.config.get("SITE_URL", "").rstrip("/")
    return configured or request.host_url.rstrip("/")


@public_bp.route("/robots.txt")
def robots():
    base = _site_base_url()
    text = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin/\n"
        "Disallow: /lang/\n"
        "\n"
        f"Sitemap: {base}/sitemap.xml\n"
    )
    return text, 200, {"Content-Type": "text/plain; charset=utf-8"}


@public_bp.route("/sitemap.xml")
def sitemap():
    base = _site_base_url()
    services = Service.query.filter_by(active=True).order_by(Service.order).all()

    # lastmod solo cuando tenemos una fecha real (una fecha inventada
    # perjudica al SEO más que omitirla).
    lastmod_home = db.session.query(db.func.max(ContentBlock.updated_at)).scalar()
    lastmod_resenas = db.session.query(db.func.max(Review.created_at)).scalar()

    def fmt(dt):
        return dt.strftime("%Y-%m-%d") if dt else None

    urls = [
        {
            "loc": base + url_for("public.index"),
            "priority": "1.0",
            "changefreq": "weekly",
            "lastmod": fmt(lastmod_home),
        },
        {
            "loc": base + url_for("public.resenas"),
            "priority": "0.7",
            "changefreq": "weekly",
            "lastmod": fmt(lastmod_resenas),
        },
        {
            "loc": base + url_for("public.cotizacion"),
            "priority": "0.8",
            "changefreq": "monthly",
            "lastmod": None,
        },
    ]
    for s in services:
        urls.append(
            {
                "loc": base + url_for("public.servicio_detalle", slug=s.slug),
                "priority": "0.8",
                "changefreq": "monthly",
                "lastmod": None,
            }
        )
    xml = render_template("sitemap.xml", urls=urls)
    return Response(xml, mimetype="application/xml")
