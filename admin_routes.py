from datetime import datetime, timedelta
from collections import defaultdict

from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import desc, func, extract
from urllib.parse import urlparse

from extensions import db
from models import Admin, Review, Quote, ContentBlock, Service, ServiceGalleryImage, EmailSettings, EmailTemplate, AdsSettings, HeroSlide, AboutSlide, QuoteGlassCard, ReviewStackCard, TrustCard
from utils import save_upload
from utils_email import send_quote_response, send_test_email, TEMPLATE_PLACEHOLDERS

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _safe_admin_next(target: str | None) -> str | None:
    """Solo permite redirecciones relativas dentro de /admin (anti open-redirect)."""
    if not target:
        return None
    target = target.strip()
    # Rechazar URLs absolutas o protocol-relative (//evil.com)
    if not target.startswith("/") or target.startswith("//") or "://" in target:
        return None
    path = urlparse(target).path or ""
    if path == "/admin" or path.startswith("/admin/"):
        return target
    return None


# ---------- Auth ----------

@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            login_user(admin)
            session.permanent = True
            flash("Welcome back.", "success")
            next_url = _safe_admin_next(request.args.get("next"))
            return redirect(next_url or url_for("admin.dashboard"))
        flash("Incorrect username or password.", "danger")

    return render_template("admin/login.html")


@admin_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("admin.login"))


# ---------- Dashboard ----------

@admin_bp.route("/")
@login_required
def dashboard():
    # Basic stats
    stats = {
        "pending_reviews": Review.query.filter_by(approved=False).count(),
        "total_reviews": Review.query.count(),
        "pending_quotes": Quote.query.filter_by(status="pendiente").count(),
        "total_quotes": Quote.query.count(),
        "total_services": Service.query.count(),
    }

    # --- Chart data: Reviews by rating (1-5 stars) ---
    reviews_by_rating = db.session.query(
        Review.rating, func.count(Review.id)
    ).filter_by(approved=True).group_by(Review.rating).all()
    reviews_rating_data = [0] * 5
    for rating, count in reviews_by_rating:
        if 1 <= rating <= 5:
            reviews_rating_data[rating - 1] = count

    # --- Chart data: Reviews by month (last 12 months) ---
    twelve_months_ago = datetime.utcnow() - timedelta(days=365)
    reviews_by_month = db.session.query(
        extract('year', Review.created_at).label('year'),
        extract('month', Review.created_at).label('month'),
        func.count(Review.id)
    ).filter(Review.created_at >= twelve_months_ago).group_by('year', 'month').order_by('year', 'month').all()

    review_months = []
    review_monthly_counts = []
    for year, month, count in reviews_by_month:
        review_months.append(f"{int(month):02d}/{int(year)}")
        review_monthly_counts.append(count)

    # --- Chart data: Quotes by status ---
    quotes_by_status = db.session.query(
        Quote.status, func.count(Quote.id)
    ).group_by(Quote.status).all()
    quote_status_labels = []
    quote_status_counts = []
    for status, count in quotes_by_status:
        quote_status_labels.append(Quote.STATUS_LABELS.get(status, status.replace('_', ' ').title()))
        quote_status_counts.append(count)

    # --- Chart data: Top 5 most quoted services ---
    top_services = db.session.query(
        Quote.service_type, func.count(Quote.id)
    ).filter(Quote.service_type.isnot(None), Quote.service_type != '').group_by(Quote.service_type).order_by(func.count(Quote.id).desc()).limit(5).all()
    top_service_labels = [s[0] for s in top_services]
    top_service_counts = [s[1] for s in top_services]

    # --- Chart data: Quotes by month (last 12 months) ---
    quotes_by_month = db.session.query(
        extract('year', Quote.created_at).label('year'),
        extract('month', Quote.created_at).label('month'),
        func.count(Quote.id)
    ).filter(Quote.created_at >= twelve_months_ago).group_by('year', 'month').order_by('year', 'month').all()

    quote_months = []
    quote_monthly_counts = []
    for year, month, count in quotes_by_month:
        quote_months.append(f"{int(month):02d}/{int(year)}")
        quote_monthly_counts.append(count)

    # --- Chart data: Average rating over time (last 12 months) ---
    avg_rating_by_month = db.session.query(
        extract('year', Review.created_at).label('year'),
        extract('month', Review.created_at).label('month'),
        func.avg(Review.rating)
    ).filter(Review.approved == True, Review.created_at >= twelve_months_ago).group_by('year', 'month').order_by('year', 'month').all()

    avg_rating_months = []
    avg_rating_values = []
    for year, month, avg in avg_rating_by_month:
        avg_rating_months.append(f"{int(month):02d}/{int(year)}")
        avg_rating_values.append(round(float(avg), 1) if avg else 0)

    recent_quotes = Quote.query.order_by(desc(Quote.created_at)).limit(5).all()
    recent_reviews = (
        Review.query.filter_by(approved=False).order_by(desc(Review.created_at)).limit(5).all()
    )
    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_quotes=recent_quotes,
        recent_reviews=recent_reviews,
        # Chart data
        reviews_rating_data=reviews_rating_data,
        review_months=review_months,
        review_monthly_counts=review_monthly_counts,
        quote_status_labels=quote_status_labels,
        quote_status_counts=quote_status_counts,
        top_service_labels=top_service_labels,
        top_service_counts=top_service_counts,
        quote_months=quote_months,
        quote_monthly_counts=quote_monthly_counts,
        avg_rating_months=avg_rating_months,
        avg_rating_values=avg_rating_values,
    )


# ---------- Reseñas ----------

@admin_bp.route("/resenas")
@login_required
def resenas():
    filtro = request.args.get("filtro", "todas")
    query = Review.query
    if filtro == "pendientes":
        query = query.filter_by(approved=False)
    elif filtro == "aprobadas":
        query = query.filter_by(approved=True)
    reviews = query.order_by(desc(Review.created_at)).all()
    return render_template("admin/resenas.html", reviews=reviews, filtro=filtro)


@admin_bp.route("/resenas/<int:review_id>/aprobar", methods=["POST"])
@login_required
def aprobar_resena(review_id):
    review = Review.query.get_or_404(review_id)
    review.approved = True
    db.session.commit()
    flash("Review approved and published.", "success")
    return redirect(url_for("admin.resenas"))


@admin_bp.route("/resenas/<int:review_id>/rechazar", methods=["POST"])
@login_required
def rechazar_resena(review_id):
    review = Review.query.get_or_404(review_id)
    review.approved = False
    db.session.commit()
    flash("Review hidden from the site.", "warning")
    return redirect(url_for("admin.resenas"))


@admin_bp.route("/resenas/<int:review_id>/eliminar", methods=["POST"])
@login_required
def eliminar_resena(review_id):
    review = Review.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()
    flash("Review deleted.", "success")
    return redirect(url_for("admin.resenas"))


@admin_bp.route("/resenas/<int:review_id>/editar", methods=["GET", "POST"])
@login_required
def editar_resena(review_id):
    review = Review.query.get_or_404(review_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        comment = request.form.get("comment", "").strip()
        try:
            rating = int(request.form.get("rating", 0))
        except (TypeError, ValueError):
            rating = 0
        if not name or not comment or rating < 1 or rating > 5:
            flash("Name, comment, and a rating from 1 to 5 are required.", "danger")
            return redirect(request.url)

        review.name = name
        review.email = request.form.get("email", "").strip()
        review.rating = rating
        review.comment = comment
        review.approved = request.form.get("approved") == "on"
        review.featured = request.form.get("featured") == "on"
        db.session.commit()
        flash("Review updated.", "success")
        return redirect(url_for("admin.resenas"))

    return render_template("admin/editar_resena.html", review=review)


# ---------- Cotizaciones (solicitudes de trabajo) ----------

@admin_bp.route("/cotizaciones")
@login_required
def cotizaciones():
    filtro = request.args.get("filtro", "todas")
    query = Quote.query
    if filtro in Quote.STATUS_CHOICES:
        query = query.filter_by(status=filtro)
    quotes = query.order_by(desc(Quote.created_at)).all()
    return render_template(
        "admin/cotizaciones.html",
        quotes=quotes,
        filtro=filtro,
        status_choices=Quote.STATUS_CHOICES,
        status_labels=Quote.STATUS_LABELS,
    )


@admin_bp.route("/cotizaciones/<int:quote_id>", methods=["GET", "POST"])
@login_required
def cotizacion_detalle(quote_id):
    quote = Quote.query.get_or_404(quote_id)
    if request.method == "POST":
        action = request.form.get("action", "guardar")
        status = request.form.get("status")
        notes = request.form.get("admin_notes", "").strip()
        if status in Quote.STATUS_CHOICES:
            quote.status = status
        quote.admin_notes = notes

        if action == "responder":
            client_response = request.form.get("client_response", "").strip()
            quote.client_response = client_response
            quote.responded_at = datetime.utcnow()
            db.session.commit()

            if not client_response:
                flash("Write a reply message before sending it to the client.", "warning")
            else:
                ok, msg = send_quote_response(quote)
                flash(
                    "Quote updated and email sent to the client." if ok
                    else f"Message saved, but the email could not be sent: {msg}",
                    "success" if ok else "warning",
                )
        else:
            db.session.commit()
            flash("Quote updated.", "success")

        return redirect(url_for("admin.cotizacion_detalle", quote_id=quote.id))

    return render_template(
        "admin/cotizacion_detalle.html",
        quote=quote,
        status_choices=Quote.STATUS_CHOICES,
        status_labels=Quote.STATUS_LABELS,
    )


@admin_bp.route("/cotizaciones/<int:quote_id>/eliminar", methods=["POST"])
@login_required
def eliminar_cotizacion(quote_id):
    quote = Quote.query.get_or_404(quote_id)
    db.session.delete(quote)
    db.session.commit()
    flash("Quote deleted.", "success")
    return redirect(url_for("admin.cotizaciones"))


# ---------- Contenido del sitio (textos e imágenes) ----------

MAX_HERO_SLIDES = 6
MAX_ABOUT_SLIDES = 10
MAX_SERVICE_GALLERY = 12
MAX_QUOTE_GLASS = 3
MAX_REVIEW_STACK = 3
MAX_TRUST_CARDS = 6


@admin_bp.route("/contenido")
@login_required
def contenido():
    blocks = ContentBlock.query.order_by(ContentBlock.label).all()
    hero_slides_count = HeroSlide.query.count()
    about_slides_count = AboutSlide.query.count()
    quote_glass_count = QuoteGlassCard.query.count()
    review_stack_count = ReviewStackCard.query.count()
    trust_cards_count = TrustCard.query.count()
    return render_template(
        "admin/contenido.html",
        blocks=blocks,
        hero_slides_count=hero_slides_count,
        about_slides_count=about_slides_count,
        quote_glass_count=quote_glass_count,
        review_stack_count=review_stack_count,
        trust_cards_count=trust_cards_count,
    )


@admin_bp.route("/contenido/<section_key>", methods=["GET", "POST"])
@login_required
def editar_contenido(section_key):
    block = ContentBlock.query.filter_by(section_key=section_key).first_or_404()
    hero_slides = []
    about_slides = []
    quote_glass_cards = []
    review_stack_cards = []
    trust_cards = []
    if section_key == "hero":
        hero_slides = HeroSlide.query.order_by(HeroSlide.sort_order, HeroSlide.id).all()
    elif section_key == "about":
        about_slides = AboutSlide.query.order_by(AboutSlide.sort_order, AboutSlide.id).all()
    elif section_key == "cotizacion":
        quote_glass_cards = QuoteGlassCard.query.order_by(QuoteGlassCard.sort_order, QuoteGlassCard.id).all()
    elif section_key == "resenas":
        review_stack_cards = ReviewStackCard.query.order_by(ReviewStackCard.sort_order, ReviewStackCard.id).all()
    elif section_key == "why_us":
        trust_cards = TrustCard.query.order_by(TrustCard.sort_order, TrustCard.id).all()

    if request.method == "POST":
        if block.section_key != "logo":
            block.eyebrow = request.form.get("eyebrow", "").strip()
            block.title = request.form.get("title", "").strip()
            block.body = request.form.get("body", "").strip()
            block.extra = request.form.get("extra", "").strip()

        # site_info usa image_path como teléfono secundario (texto, no imagen)
        if block.section_key == "site_info":
            block.image_path = request.form.get("image_path", "").strip()

        # Logo y bloques sin galería propia siguen con imagen única
        if block.section_key not in ("hero", "about", "cotizacion", "resenas", "site_info"):
            image = request.files.get("image")
            if image and image.filename:
                rel_path = save_upload(image, "content")
                if rel_path:
                    block.image_path = rel_path

        db.session.commit()
        flash(f'Block "{block.label}" updated.', "success")
        return redirect(url_for("admin.contenido"))

    return render_template(
        "admin/editar_contenido.html",
        block=block,
        hero_slides=hero_slides,
        about_slides=about_slides,
        quote_glass_cards=quote_glass_cards,
        review_stack_cards=review_stack_cards,
        trust_cards=trust_cards,
        max_hero_slides=MAX_HERO_SLIDES,
        max_about_slides=MAX_ABOUT_SLIDES,
        max_quote_glass=MAX_QUOTE_GLASS,
        max_review_stack=MAX_REVIEW_STACK,
        max_trust_cards=MAX_TRUST_CARDS,
        trust_icon_choices=TrustCard.ICON_CHOICES,
    )


@admin_bp.route("/contenido/hero/slides", methods=["POST"])
@login_required
def hero_slides_add():
    files = request.files.getlist("images")
    current = HeroSlide.query.count()
    added = 0
    for f in files:
        if current + added >= MAX_HERO_SLIDES:
            break
        if not f or not f.filename:
            continue
        rel_path = save_upload(f, "content")
        if not rel_path:
            continue
        caption = request.form.get("caption", "").strip() or None
        max_order = db.session.query(db.func.coalesce(db.func.max(HeroSlide.sort_order), -1)).scalar()
        db.session.add(
            HeroSlide(
                image_path=rel_path,
                caption=caption,
                sort_order=(max_order or 0) + 1 + added,
                active=True,
            )
        )
        added += 1
    if added:
        db.session.commit()
        flash(f"Added {added} image(s) to the hero gallery.", "success")
    else:
        flash("Could not add any images. Check the format (png/jpg/webp) and the limit of 6.", "warning")
    return redirect(url_for("admin.editar_contenido", section_key="hero"))


@admin_bp.route("/contenido/hero/slides/<int:slide_id>/eliminar", methods=["POST"])
@login_required
def hero_slide_delete(slide_id):
    slide = HeroSlide.query.get_or_404(slide_id)
    db.session.delete(slide)
    db.session.commit()
    flash("Image removed from the gallery.", "success")
    return redirect(url_for("admin.editar_contenido", section_key="hero"))


@admin_bp.route("/contenido/hero/slides/<int:slide_id>/mover", methods=["POST"])
@login_required
def hero_slide_move(slide_id):
    direction = request.form.get("direction", "up")
    slides = HeroSlide.query.order_by(HeroSlide.sort_order, HeroSlide.id).all()
    idx = next((i for i, s in enumerate(slides) if s.id == slide_id), None)
    if idx is None:
        flash("Image not found.", "danger")
        return redirect(url_for("admin.editar_contenido", section_key="hero"))
    swap_with = idx - 1 if direction == "up" else idx + 1
    if 0 <= swap_with < len(slides):
        slides[idx].sort_order, slides[swap_with].sort_order = (
            slides[swap_with].sort_order,
            slides[idx].sort_order,
        )
        # Si tenían el mismo order, forzar diferencia
        if slides[idx].sort_order == slides[swap_with].sort_order:
            slides[idx].sort_order = swap_with
            slides[swap_with].sort_order = idx
        db.session.commit()
    return redirect(url_for("admin.editar_contenido", section_key="hero"))


@admin_bp.route("/contenido/hero/slides/<int:slide_id>/toggle", methods=["POST"])
@login_required
def hero_slide_toggle(slide_id):
    slide = HeroSlide.query.get_or_404(slide_id)
    slide.active = not slide.active
    db.session.commit()
    flash("Image " + ("visible" if slide.active else "hidden") + " on the site.", "success")
    return redirect(url_for("admin.editar_contenido", section_key="hero"))


@admin_bp.route("/contenido/hero/slides/<int:slide_id>/caption", methods=["POST"])
@login_required
def hero_slide_caption(slide_id):
    slide = HeroSlide.query.get_or_404(slide_id)
    slide.caption = request.form.get("caption", "").strip() or None
    db.session.commit()
    flash("Caption updated.", "success")
    return redirect(url_for("admin.editar_contenido", section_key="hero"))


@admin_bp.route("/contenido/about/slides", methods=["POST"])
@login_required
def about_slides_add():
    files = request.files.getlist("images")
    current = AboutSlide.query.count()
    added = 0
    for f in files:
        if current + added >= MAX_ABOUT_SLIDES:
            break
        if not f or not f.filename:
            continue
        rel_path = save_upload(f, "content")
        if not rel_path:
            continue
        max_order = db.session.query(db.func.coalesce(db.func.max(AboutSlide.sort_order), -1)).scalar()
        db.session.add(
            AboutSlide(
                image_path=rel_path,
                sort_order=(max_order or 0) + 1 + added,
                active=True,
            )
        )
        added += 1
    if added:
        db.session.commit()
        flash(f"Added {added} image(s) to the About Us gallery.", "success")
    else:
        flash("Could not add any images. Check the format and the limit of 10.", "warning")
    return redirect(url_for("admin.editar_contenido", section_key="about"))


@admin_bp.route("/contenido/about/slides/<int:slide_id>/eliminar", methods=["POST"])
@login_required
def about_slide_delete(slide_id):
    slide = AboutSlide.query.get_or_404(slide_id)
    db.session.delete(slide)
    db.session.commit()
    flash("Image removed from the gallery.", "success")
    return redirect(url_for("admin.editar_contenido", section_key="about"))


@admin_bp.route("/contenido/about/slides/<int:slide_id>/mover", methods=["POST"])
@login_required
def about_slide_move(slide_id):
    direction = request.form.get("direction", "up")
    slides = AboutSlide.query.order_by(AboutSlide.sort_order, AboutSlide.id).all()
    idx = next((i for i, s in enumerate(slides) if s.id == slide_id), None)
    if idx is None:
        flash("Image not found.", "danger")
        return redirect(url_for("admin.editar_contenido", section_key="about"))
    swap_with = idx - 1 if direction == "up" else idx + 1
    if 0 <= swap_with < len(slides):
        slides[idx].sort_order, slides[swap_with].sort_order = (
            slides[swap_with].sort_order,
            slides[idx].sort_order,
        )
        if slides[idx].sort_order == slides[swap_with].sort_order:
            slides[idx].sort_order = swap_with
            slides[swap_with].sort_order = idx
        db.session.commit()
    return redirect(url_for("admin.editar_contenido", section_key="about"))


@admin_bp.route("/contenido/about/slides/<int:slide_id>/toggle", methods=["POST"])
@login_required
def about_slide_toggle(slide_id):
    slide = AboutSlide.query.get_or_404(slide_id)
    slide.active = not slide.active
    db.session.commit()
    flash("Image " + ("visible" if slide.active else "hidden") + " on the site.", "success")
    return redirect(url_for("admin.editar_contenido", section_key="about"))


# ---------- Cards glass de cotización ----------

@admin_bp.route("/contenido/cotizacion/glass", methods=["POST"])
@login_required
def quote_glass_add():
    files = request.files.getlist("images")
    current = QuoteGlassCard.query.count()
    added = 0
    default_caption = request.form.get("caption", "").strip() or None
    for f in files:
        if current + added >= MAX_QUOTE_GLASS:
            break
        if not f or not f.filename:
            continue
        rel_path = save_upload(f, "content")
        if not rel_path:
            continue
        max_order = db.session.query(db.func.coalesce(db.func.max(QuoteGlassCard.sort_order), -1)).scalar()
        db.session.add(
            QuoteGlassCard(
                image_path=rel_path,
                caption=default_caption,
                sort_order=(max_order or 0) + 1 + added,
                active=True,
            )
        )
        added += 1
    if added:
        db.session.commit()
        flash(f"Added {added} image(s) to the quote cards.", "success")
    else:
        flash("Could not add any images. Check the format and the limit of 3.", "warning")
    return redirect(url_for("admin.editar_contenido", section_key="cotizacion"))


@admin_bp.route("/contenido/cotizacion/glass/<int:card_id>/eliminar", methods=["POST"])
@login_required
def quote_glass_delete(card_id):
    card = QuoteGlassCard.query.get_or_404(card_id)
    db.session.delete(card)
    db.session.commit()
    flash("Image removed from the quote cards.", "success")
    return redirect(url_for("admin.editar_contenido", section_key="cotizacion"))


@admin_bp.route("/contenido/cotizacion/glass/<int:card_id>/mover", methods=["POST"])
@login_required
def quote_glass_move(card_id):
    direction = request.form.get("direction", "up")
    cards = QuoteGlassCard.query.order_by(QuoteGlassCard.sort_order, QuoteGlassCard.id).all()
    idx = next((i for i, c in enumerate(cards) if c.id == card_id), None)
    if idx is None:
        flash("Image not found.", "danger")
        return redirect(url_for("admin.editar_contenido", section_key="cotizacion"))
    swap_with = idx - 1 if direction == "up" else idx + 1
    if 0 <= swap_with < len(cards):
        cards[idx].sort_order, cards[swap_with].sort_order = (
            cards[swap_with].sort_order,
            cards[idx].sort_order,
        )
        if cards[idx].sort_order == cards[swap_with].sort_order:
            cards[idx].sort_order = swap_with
            cards[swap_with].sort_order = idx
        db.session.commit()
    return redirect(url_for("admin.editar_contenido", section_key="cotizacion"))


@admin_bp.route("/contenido/cotizacion/glass/<int:card_id>/toggle", methods=["POST"])
@login_required
def quote_glass_toggle(card_id):
    card = QuoteGlassCard.query.get_or_404(card_id)
    card.active = not card.active
    db.session.commit()
    flash("Card " + ("visible" if card.active else "hidden") + " on the site.", "success")
    return redirect(url_for("admin.editar_contenido", section_key="cotizacion"))


@admin_bp.route("/contenido/cotizacion/glass/<int:card_id>/caption", methods=["POST"])
@login_required
def quote_glass_caption(card_id):
    card = QuoteGlassCard.query.get_or_404(card_id)
    card.caption = request.form.get("caption", "").strip() or None
    db.session.commit()
    flash("Card text updated.", "success")
    return redirect(url_for("admin.editar_contenido", section_key="cotizacion"))


# ---------- Cards apiladas de reseñas ----------

@admin_bp.route("/contenido/resenas/stack", methods=["POST"])
@login_required
def review_stack_add():
    files = request.files.getlist("images")
    current = ReviewStackCard.query.count()
    added = 0
    default_caption = request.form.get("caption", "").strip() or None
    default_button = request.form.get("button_label", "").strip() or None
    for f in files:
        if current + added >= MAX_REVIEW_STACK:
            break
        if not f or not f.filename:
            continue
        rel_path = save_upload(f, "content")
        if not rel_path:
            continue
        max_order = db.session.query(db.func.coalesce(db.func.max(ReviewStackCard.sort_order), -1)).scalar()
        db.session.add(
            ReviewStackCard(
                image_path=rel_path,
                caption=default_caption,
                button_label=default_button,
                sort_order=(max_order or 0) + 1 + added,
                active=True,
            )
        )
        added += 1
    if added:
        db.session.commit()
        flash(f"Added {added} image(s) to the review cards.", "success")
    else:
        flash("Could not add any images. Check the format and the limit of 3.", "warning")
    return redirect(url_for("admin.editar_contenido", section_key="resenas"))


@admin_bp.route("/contenido/resenas/stack/<int:card_id>/eliminar", methods=["POST"])
@login_required
def review_stack_delete(card_id):
    card = ReviewStackCard.query.get_or_404(card_id)
    db.session.delete(card)
    db.session.commit()
    flash("Image removed from the review cards.", "success")
    return redirect(url_for("admin.editar_contenido", section_key="resenas"))


@admin_bp.route("/contenido/resenas/stack/<int:card_id>/mover", methods=["POST"])
@login_required
def review_stack_move(card_id):
    direction = request.form.get("direction", "up")
    cards = ReviewStackCard.query.order_by(ReviewStackCard.sort_order, ReviewStackCard.id).all()
    idx = next((i for i, c in enumerate(cards) if c.id == card_id), None)
    if idx is None:
        flash("Image not found.", "danger")
        return redirect(url_for("admin.editar_contenido", section_key="resenas"))
    swap_with = idx - 1 if direction == "up" else idx + 1
    if 0 <= swap_with < len(cards):
        cards[idx].sort_order, cards[swap_with].sort_order = (
            cards[swap_with].sort_order,
            cards[idx].sort_order,
        )
        if cards[idx].sort_order == cards[swap_with].sort_order:
            cards[idx].sort_order = swap_with
            cards[swap_with].sort_order = idx
        db.session.commit()
    return redirect(url_for("admin.editar_contenido", section_key="resenas"))


@admin_bp.route("/contenido/resenas/stack/<int:card_id>/toggle", methods=["POST"])
@login_required
def review_stack_toggle(card_id):
    card = ReviewStackCard.query.get_or_404(card_id)
    card.active = not card.active
    db.session.commit()
    flash("Card " + ("visible" if card.active else "hidden") + " on the site.", "success")
    return redirect(url_for("admin.editar_contenido", section_key="resenas"))


@admin_bp.route("/contenido/resenas/stack/<int:card_id>/caption", methods=["POST"])
@login_required
def review_stack_caption(card_id):
    card = ReviewStackCard.query.get_or_404(card_id)
    card.caption = request.form.get("caption", "").strip() or None
    card.button_label = request.form.get("button_label", "").strip() or None
    db.session.commit()
    flash("Card texts updated.", "success")
    return redirect(url_for("admin.editar_contenido", section_key="resenas"))


# ---------- Trust cards (What sets us apart) ----------

@admin_bp.route("/contenido/why_us/cards", methods=["POST"])
@login_required
def trust_card_add():
    if TrustCard.query.count() >= MAX_TRUST_CARDS:
        flash(f"Limit of {MAX_TRUST_CARDS} highlight cards reached.", "warning")
        return redirect(url_for("admin.editar_contenido", section_key="why_us"))

    metric = request.form.get("metric", "").strip()
    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    icon_key = request.form.get("icon_key", "shield").strip()
    if icon_key not in TrustCard.ICON_CHOICES:
        icon_key = "shield"

    if not metric or not title:
        flash("Metric and title are required.", "danger")
        return redirect(url_for("admin.editar_contenido", section_key="why_us"))

    image_path = None
    image = request.files.get("image")
    if image and image.filename:
        image_path = save_upload(image, "content")

    max_order = db.session.query(db.func.coalesce(db.func.max(TrustCard.sort_order), -1)).scalar()
    db.session.add(
        TrustCard(
            metric=metric,
            title=title,
            body=body or None,
            icon_key=icon_key,
            image_path=image_path,
            sort_order=(max_order or 0) + 1,
            active=True,
        )
    )
    db.session.commit()
    flash("Highlight card added.", "success")
    return redirect(url_for("admin.editar_contenido", section_key="why_us"))


@admin_bp.route("/contenido/why_us/cards/<int:card_id>/guardar", methods=["POST"])
@login_required
def trust_card_save(card_id):
    card = TrustCard.query.get_or_404(card_id)
    metric = request.form.get("metric", "").strip()
    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    icon_key = request.form.get("icon_key", card.icon_key or "shield").strip()
    if icon_key not in TrustCard.ICON_CHOICES:
        icon_key = "shield"

    if not metric or not title:
        flash("Metric and title are required.", "danger")
        return redirect(url_for("admin.editar_contenido", section_key="why_us"))

    card.metric = metric
    card.title = title
    card.body = body or None
    card.icon_key = icon_key

    image = request.files.get("image")
    if image and image.filename:
        rel_path = save_upload(image, "content")
        if rel_path:
            card.image_path = rel_path

    if request.form.get("remove_image") == "on":
        card.image_path = None

    db.session.commit()
    flash("Highlight card updated.", "success")
    return redirect(url_for("admin.editar_contenido", section_key="why_us"))


@admin_bp.route("/contenido/why_us/cards/<int:card_id>/eliminar", methods=["POST"])
@login_required
def trust_card_delete(card_id):
    card = TrustCard.query.get_or_404(card_id)
    db.session.delete(card)
    db.session.commit()
    flash("Highlight card deleted.", "success")
    return redirect(url_for("admin.editar_contenido", section_key="why_us"))


@admin_bp.route("/contenido/why_us/cards/<int:card_id>/mover", methods=["POST"])
@login_required
def trust_card_move(card_id):
    direction = request.form.get("direction", "up")
    cards = TrustCard.query.order_by(TrustCard.sort_order, TrustCard.id).all()
    idx = next((i for i, c in enumerate(cards) if c.id == card_id), None)
    if idx is None:
        flash("Card not found.", "danger")
        return redirect(url_for("admin.editar_contenido", section_key="why_us"))
    swap_with = idx - 1 if direction == "up" else idx + 1
    if 0 <= swap_with < len(cards):
        cards[idx].sort_order, cards[swap_with].sort_order = (
            cards[swap_with].sort_order,
            cards[idx].sort_order,
        )
        if cards[idx].sort_order == cards[swap_with].sort_order:
            cards[idx].sort_order = swap_with
            cards[swap_with].sort_order = idx
        db.session.commit()
    return redirect(url_for("admin.editar_contenido", section_key="why_us"))


@admin_bp.route("/contenido/why_us/cards/<int:card_id>/toggle", methods=["POST"])
@login_required
def trust_card_toggle(card_id):
    card = TrustCard.query.get_or_404(card_id)
    card.active = not card.active
    db.session.commit()
    flash("Card " + ("visible" if card.active else "hidden") + " on the site.", "success")
    return redirect(url_for("admin.editar_contenido", section_key="why_us"))


# ---------- Servicios / Productos ----------

@admin_bp.route("/servicios")
@login_required
def servicios():
    services = Service.query.order_by(Service.order).all()
    return render_template("admin/servicios.html", services=services)


@admin_bp.route("/servicios/nuevo", methods=["GET", "POST"])
@login_required
def nuevo_servicio():
    if request.method == "POST":
        return _guardar_servicio(None)
    return render_template(
        "admin/editar_servicio.html",
        servicio=None,
        gallery=[],
        max_gallery=MAX_SERVICE_GALLERY,
    )


@admin_bp.route("/servicios/<int:service_id>/editar", methods=["GET", "POST"])
@login_required
def editar_servicio(service_id):
    servicio = Service.query.get_or_404(service_id)
    if request.method == "POST":
        return _guardar_servicio(servicio)
    gallery = (
        ServiceGalleryImage.query.filter_by(service_id=servicio.id)
        .order_by(ServiceGalleryImage.sort_order, ServiceGalleryImage.id)
        .all()
    )
    return render_template(
        "admin/editar_servicio.html",
        servicio=servicio,
        gallery=gallery,
        max_gallery=MAX_SERVICE_GALLERY,
    )


def _guardar_servicio(servicio):
    slug = request.form.get("slug", "").strip().lower().replace(" ", "-")
    name = request.form.get("name", "").strip()
    short_description = request.form.get("short_description", "").strip()
    description = request.form.get("description", "").strip()
    work_methods = request.form.get("work_methods", "").strip()
    order = request.form.get("order", 0)
    active = request.form.get("active") == "on"

    if not slug or not name:
        flash("Name and slug are required.", "danger")
        return redirect(request.url)

    # Evitar UNIQUE constraint failed en services.slug
    existing = Service.query.filter_by(slug=slug).first()
    if existing and (servicio is None or existing.id != servicio.id):
        flash(
            f'A product with the slug "{slug}" already exists. '
            "Use a different slug (for example by adding a suffix) or edit the existing product.",
            "danger",
        )
        return redirect(request.url)

    if servicio is None:
        servicio = Service()
        db.session.add(servicio)

    servicio.slug = slug
    servicio.name = name
    servicio.short_description = short_description
    servicio.description = description
    servicio.work_methods = work_methods or None
    try:
        servicio.order = int(order)
    except (TypeError, ValueError):
        servicio.order = 0
    servicio.active = active

    image = request.files.get("image")
    if image and image.filename:
        rel_path = save_upload(image, "content")
        if rel_path:
            servicio.image_path = rel_path
        else:
            flash("The cover image could not be uploaded (use png/jpg/webp).", "warning")

    video = request.files.get("video")
    if video and video.filename:
        rel_path = save_upload(video, "content", media="video")
        if rel_path:
            servicio.video_path = rel_path
        else:
            flash("The video could not be uploaded (use mp4/webm/mov, max. 64 MB).", "warning")

    if request.form.get("remove_video") == "on":
        servicio.video_path = None

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash(
            f'Could not save: the slug "{slug}" is already in use by another product.',
            "danger",
        )
        return redirect(request.url)

    flash(f'Service "{servicio.name}" saved.', "success")
    return redirect(url_for("admin.editar_servicio", service_id=servicio.id))


@admin_bp.route("/servicios/<int:service_id>/galeria", methods=["POST"])
@login_required
def service_gallery_add(service_id):
    servicio = Service.query.get_or_404(service_id)
    files = request.files.getlist("images")
    current = ServiceGalleryImage.query.filter_by(service_id=servicio.id).count()
    added = 0
    for f in files:
        if current + added >= MAX_SERVICE_GALLERY:
            break
        if not f or not f.filename:
            continue
        rel_path = save_upload(f, "content")
        if not rel_path:
            continue
        caption = request.form.get("caption", "").strip() or None
        max_order = db.session.query(
            db.func.coalesce(db.func.max(ServiceGalleryImage.sort_order), -1)
        ).filter(ServiceGalleryImage.service_id == servicio.id).scalar()
        db.session.add(
            ServiceGalleryImage(
                service_id=servicio.id,
                image_path=rel_path,
                caption=caption,
                sort_order=(max_order or 0) + 1 + added,
                active=True,
            )
        )
        added += 1
    if added:
        db.session.commit()
        flash(f"Added {added} photo(s) to the gallery.", "success")
    else:
        flash("Could not add any photos. Check the format (png/jpg/webp) and the limit.", "warning")
    return redirect(url_for("admin.editar_servicio", service_id=servicio.id))


@admin_bp.route("/servicios/galeria/<int:image_id>/eliminar", methods=["POST"])
@login_required
def service_gallery_delete(image_id):
    img = ServiceGalleryImage.query.get_or_404(image_id)
    service_id = img.service_id
    db.session.delete(img)
    db.session.commit()
    flash("Photo removed from the gallery.", "success")
    return redirect(url_for("admin.editar_servicio", service_id=service_id))


@admin_bp.route("/servicios/galeria/<int:image_id>/mover", methods=["POST"])
@login_required
def service_gallery_move(image_id):
    direction = request.form.get("direction", "up")
    img = ServiceGalleryImage.query.get_or_404(image_id)
    slides = (
        ServiceGalleryImage.query.filter_by(service_id=img.service_id)
        .order_by(ServiceGalleryImage.sort_order, ServiceGalleryImage.id)
        .all()
    )
    idx = next((i for i, s in enumerate(slides) if s.id == image_id), None)
    if idx is None:
        flash("Image not found.", "danger")
        return redirect(url_for("admin.editar_servicio", service_id=img.service_id))
    swap_with = idx - 1 if direction == "up" else idx + 1
    if 0 <= swap_with < len(slides):
        slides[idx].sort_order, slides[swap_with].sort_order = (
            slides[swap_with].sort_order,
            slides[idx].sort_order,
        )
        if slides[idx].sort_order == slides[swap_with].sort_order:
            slides[idx].sort_order = swap_with
            slides[swap_with].sort_order = idx
        db.session.commit()
    return redirect(url_for("admin.editar_servicio", service_id=img.service_id))


@admin_bp.route("/servicios/galeria/<int:image_id>/toggle", methods=["POST"])
@login_required
def service_gallery_toggle(image_id):
    img = ServiceGalleryImage.query.get_or_404(image_id)
    img.active = not img.active
    db.session.commit()
    flash("Photo visibility updated.", "success")
    return redirect(url_for("admin.editar_servicio", service_id=img.service_id))


@admin_bp.route("/servicios/galeria/<int:image_id>/caption", methods=["POST"])
@login_required
def service_gallery_caption(image_id):
    img = ServiceGalleryImage.query.get_or_404(image_id)
    img.caption = request.form.get("caption", "").strip() or None
    db.session.commit()
    flash("Caption saved.", "success")
    return redirect(url_for("admin.editar_servicio", service_id=img.service_id))


@admin_bp.route("/servicios/<int:service_id>/eliminar", methods=["POST"])
@login_required
def eliminar_servicio(service_id):
    servicio = Service.query.get_or_404(service_id)
    db.session.delete(servicio)
    db.session.commit()
    flash("Service deleted.", "success")
    return redirect(url_for("admin.servicios"))


# ---------- Configuración de correo (SMTP / Gmail) ----------

@admin_bp.route("/configuracion/correo", methods=["GET", "POST"])
@login_required
def config_correo():
    settings = EmailSettings.query.first()
    if not settings:
        settings = EmailSettings(smtp_host="smtp.gmail.com", smtp_port=587)
        db.session.add(settings)
        db.session.commit()

    if request.method == "POST":
        settings.enabled = request.form.get("enabled") == "on"
        settings.smtp_host = request.form.get("smtp_host", "smtp.gmail.com").strip() or "smtp.gmail.com"
        try:
            settings.smtp_port = int(request.form.get("smtp_port", 587))
        except (TypeError, ValueError):
            settings.smtp_port = 587
        settings.smtp_email = request.form.get("smtp_email", "").strip()
        settings.sender_name = request.form.get("sender_name", "").strip()
        settings.notify_email = request.form.get("notify_email", "").strip()

        new_password = request.form.get("smtp_app_password", "").strip()
        if new_password:
            settings.smtp_app_password = new_password

        db.session.commit()
        flash("Email settings updated.", "success")
        return redirect(url_for("admin.config_correo"))

    return render_template("admin/config_correo.html", settings=settings)


@admin_bp.route("/configuracion/correo/probar", methods=["POST"])
@login_required
def config_correo_probar():
    settings = EmailSettings.query.first()
    if not settings:
        flash("Save the email settings first.", "warning")
        return redirect(url_for("admin.config_correo"))

    ok, msg = send_test_email(settings)
    flash(
        f"Test email sent to {settings.notify_email or settings.smtp_email}." if ok
        else f"Could not send the test email: {msg}",
        "success" if ok else "danger",
    )
    return redirect(url_for("admin.config_correo"))


# ---------- Plantillas de correo ----------

@admin_bp.route("/configuracion/plantillas")
@login_required
def plantillas():
    templates = EmailTemplate.query.order_by(EmailTemplate.label).all()
    return render_template("admin/plantillas.html", templates=templates)


@admin_bp.route("/configuracion/plantillas/<key>", methods=["GET", "POST"])
@login_required
def editar_plantilla(key):
    tpl = EmailTemplate.query.filter_by(key=key).first_or_404()

    if request.method == "POST":
        tpl.subject = request.form.get("subject", "").strip()
        tpl.body = request.form.get("body", "").strip()
        db.session.commit()
        flash(f'Template "{tpl.label}" updated.', "success")
        return redirect(url_for("admin.plantillas"))

    return render_template(
        "admin/editar_plantilla.html",
        tpl=tpl,
        placeholders=TEMPLATE_PLACEHOLDERS.get(tpl.key, []),
    )


# ---------- Usuarios admin ----------

def superadmin_required(f):
    """Decorator: solo superadmins acceden a la vista."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_superadmin:
            flash("You do not have permission to access this section.", "danger")
            return redirect(url_for("admin.dashboard"))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route("/usuarios")
@superadmin_required
def usuarios():
    admins = Admin.query.order_by(Admin.created_at).all()
    superadmin_count = sum(1 for a in admins if a.is_superadmin)
    return render_template(
        "admin/usuarios.html",
        admins=admins,
        superadmin_count=superadmin_count,
    )


@admin_bp.route("/usuarios/nuevo", methods=["GET", "POST"])
@superadmin_required
def nuevo_usuario():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        is_superadmin = request.form.get("is_superadmin") == "on"

        if not username or not password:
            flash("Username and password are required.", "danger")
            return redirect(url_for("admin.nuevo_usuario"))

        if Admin.query.filter_by(username=username).first():
            flash("A user with that name already exists.", "danger")
            return redirect(url_for("admin.nuevo_usuario"))

        new_admin = Admin(username=username, is_superadmin=is_superadmin)
        new_admin.set_password(password)
        db.session.add(new_admin)
        db.session.commit()
        flash(f'User "{username}" created.', "success")
        return redirect(url_for("admin.usuarios"))

    return render_template("admin/editar_usuario.html", admin_user=None)


@admin_bp.route("/usuarios/<int:user_id>/editar", methods=["GET", "POST"])
@superadmin_required
def editar_usuario(user_id):
    admin_user = Admin.query.get_or_404(user_id)

    if request.method == "POST":
        new_username = request.form.get("username", "").strip()
        new_password = request.form.get("password", "")
        new_superadmin = request.form.get("is_superadmin") == "on"

        if not new_username:
            flash("Username is required.", "danger")
            return redirect(url_for("admin.editar_usuario", user_id=user_id))

        existing = Admin.query.filter_by(username=new_username).first()
        if existing and existing.id != user_id:
            flash("Another user with that name already exists.", "danger")
            return redirect(url_for("admin.editar_usuario", user_id=user_id))

        admin_user.username = new_username
        admin_user.is_superadmin = new_superadmin

        if new_password:
            admin_user.set_password(new_password)

        db.session.commit()
        flash(f'User "{new_username}" updated.', "success")
        return redirect(url_for("admin.usuarios"))

    return render_template("admin/editar_usuario.html", admin_user=admin_user)


@admin_bp.route("/usuarios/<int:user_id>/eliminar", methods=["POST"])
@superadmin_required
def eliminar_usuario(user_id):
    admin_user = Admin.query.get_or_404(user_id)

    if admin_user.id == current_user.id:
        flash("You cannot delete yourself.", "danger")
        return redirect(url_for("admin.usuarios"))

    if admin_user.is_superadmin:
        superadmin_count = Admin.query.filter_by(is_superadmin=True).count()
        if superadmin_count <= 1:
            flash("You cannot delete the last superadmin.", "danger")
            return redirect(url_for("admin.usuarios"))

    db.session.delete(admin_user)
    db.session.commit()
    flash(f'User "{admin_user.username}" deleted.', "success")
    return redirect(url_for("admin.usuarios"))


@admin_bp.route("/usuarios/<int:user_id>/toggle-superadmin", methods=["POST"])
@superadmin_required
def toggle_superadmin(user_id):
    admin_user = Admin.query.get_or_404(user_id)

    if admin_user.id == current_user.id:
        flash("You cannot change your own superadmin permission.", "danger")
        return redirect(url_for("admin.usuarios"))

    if admin_user.is_superadmin:
        superadmin_count = Admin.query.filter_by(is_superadmin=True).count()
        if superadmin_count <= 1:
            flash("You cannot remove superadmin from the last superadmin.", "danger")
            return redirect(url_for("admin.usuarios"))

    admin_user.is_superadmin = not admin_user.is_superadmin
    db.session.commit()

    estado = "granted" if admin_user.is_superadmin else "revoked"
    flash(f'Superadmin permission {estado} for "{admin_user.username}".', "success")
    return redirect(url_for("admin.usuarios"))


# ---------- Marketing: Google Ads / Analytics ----------

@admin_bp.route("/configuracion/marketing", methods=["GET", "POST"])
@login_required
def config_marketing():
    settings = AdsSettings.query.first()
    if not settings:
        settings = AdsSettings()
        db.session.add(settings)
        db.session.commit()

    if request.method == "POST":
        settings.enabled = request.form.get("enabled") == "on"
        settings.google_ads_id = request.form.get("google_ads_id", "").strip()
        settings.conversion_label = request.form.get("conversion_label", "").strip()
        settings.ga4_measurement_id = request.form.get("ga4_measurement_id", "").strip()
        db.session.commit()
        flash("Google Ads settings updated.", "success")
        return redirect(url_for("admin.config_marketing"))

    return render_template("admin/config_marketing.html", settings=settings)
