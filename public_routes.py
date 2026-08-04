from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy import desc

from extensions import db
from models import ContentBlock, Service, Review, Quote, QuoteImage
from utils import save_upload
from utils_email import notify_new_review, notify_new_quote

public_bp = Blueprint("public", __name__)


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

    return render_template("cotizacion.html", services=services)


@public_bp.route("/cotizacion/gracias")
def cotizacion_gracias():
    return render_template("cotizacion_gracias.html")
