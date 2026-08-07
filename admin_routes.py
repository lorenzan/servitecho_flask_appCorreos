from datetime import datetime

from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import desc

from extensions import db
from models import Admin, Review, Quote, ContentBlock, Service, EmailSettings, EmailTemplate, HeroSlide, AboutSlide
from utils import save_upload
from utils_email import send_quote_response, send_test_email, TEMPLATE_PLACEHOLDERS

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


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
            flash("Bienvenido de nuevo.", "success")
            next_url = request.args.get("next")
            return redirect(next_url or url_for("admin.dashboard"))
        flash("Usuario o contraseña incorrectos.", "danger")

    return render_template("admin/login.html")


@admin_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada.", "success")
    return redirect(url_for("admin.login"))


# ---------- Dashboard ----------

@admin_bp.route("/")
@login_required
def dashboard():
    stats = {
        "pending_reviews": Review.query.filter_by(approved=False).count(),
        "total_reviews": Review.query.count(),
        "pending_quotes": Quote.query.filter_by(status="pendiente").count(),
        "total_quotes": Quote.query.count(),
        "total_services": Service.query.count(),
    }
    recent_quotes = Quote.query.order_by(desc(Quote.created_at)).limit(5).all()
    recent_reviews = (
        Review.query.filter_by(approved=False).order_by(desc(Review.created_at)).limit(5).all()
    )
    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_quotes=recent_quotes,
        recent_reviews=recent_reviews,
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
    flash("Reseña aprobada y publicada.", "success")
    return redirect(url_for("admin.resenas"))


@admin_bp.route("/resenas/<int:review_id>/rechazar", methods=["POST"])
@login_required
def rechazar_resena(review_id):
    review = Review.query.get_or_404(review_id)
    review.approved = False
    db.session.commit()
    flash("Reseña ocultada del sitio.", "warning")
    return redirect(url_for("admin.resenas"))


@admin_bp.route("/resenas/<int:review_id>/eliminar", methods=["POST"])
@login_required
def eliminar_resena(review_id):
    review = Review.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()
    flash("Reseña eliminada.", "success")
    return redirect(url_for("admin.resenas"))


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
                flash("Escribe un mensaje de respuesta antes de enviarlo al cliente.", "warning")
            else:
                ok, msg = send_quote_response(quote)
                flash(
                    "Cotización actualizada y correo enviado al cliente." if ok
                    else f"Se guardó el mensaje, pero no se pudo enviar el correo: {msg}",
                    "success" if ok else "warning",
                )
        else:
            db.session.commit()
            flash("Cotización actualizada.", "success")

        return redirect(url_for("admin.cotizacion_detalle", quote_id=quote.id))

    return render_template(
        "admin/cotizacion_detalle.html", quote=quote, status_choices=Quote.STATUS_CHOICES
    )


@admin_bp.route("/cotizaciones/<int:quote_id>/eliminar", methods=["POST"])
@login_required
def eliminar_cotizacion(quote_id):
    quote = Quote.query.get_or_404(quote_id)
    db.session.delete(quote)
    db.session.commit()
    flash("Cotización eliminada.", "success")
    return redirect(url_for("admin.cotizaciones"))


# ---------- Contenido del sitio (textos e imágenes) ----------

MAX_HERO_SLIDES = 6
MAX_ABOUT_SLIDES = 10


@admin_bp.route("/contenido")
@login_required
def contenido():
    blocks = ContentBlock.query.order_by(ContentBlock.label).all()
    hero_slides_count = HeroSlide.query.count()
    about_slides_count = AboutSlide.query.count()
    return render_template(
        "admin/contenido.html",
        blocks=blocks,
        hero_slides_count=hero_slides_count,
        about_slides_count=about_slides_count,
    )


@admin_bp.route("/contenido/<section_key>", methods=["GET", "POST"])
@login_required
def editar_contenido(section_key):
    block = ContentBlock.query.filter_by(section_key=section_key).first_or_404()
    hero_slides = []
    about_slides = []
    if section_key == "hero":
        hero_slides = HeroSlide.query.order_by(HeroSlide.sort_order, HeroSlide.id).all()
    elif section_key == "about":
        about_slides = AboutSlide.query.order_by(AboutSlide.sort_order, AboutSlide.id).all()

    if request.method == "POST":
        if block.section_key != "logo":
            block.eyebrow = request.form.get("eyebrow", "").strip()
            block.title = request.form.get("title", "").strip()
            block.body = request.form.get("body", "").strip()
            block.extra = request.form.get("extra", "").strip()

        # Logo y bloques sin galería propia siguen con imagen única
        if block.section_key not in ("hero", "about"):
            image = request.files.get("image")
            if image and image.filename:
                rel_path = save_upload(image, "content")
                if rel_path:
                    block.image_path = rel_path

        db.session.commit()
        flash(f'Bloque "{block.label}" actualizado.', "success")
        return redirect(url_for("admin.contenido"))

    return render_template(
        "admin/editar_contenido.html",
        block=block,
        hero_slides=hero_slides,
        about_slides=about_slides,
        max_hero_slides=MAX_HERO_SLIDES,
        max_about_slides=MAX_ABOUT_SLIDES,
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
        flash(f"Se agregaron {added} imagen(es) a la galería del hero.", "success")
    else:
        flash("No se pudo agregar ninguna imagen. Revisa el formato (png/jpg/webp) y el límite de 6.", "warning")
    return redirect(url_for("admin.editar_contenido", section_key="hero"))


@admin_bp.route("/contenido/hero/slides/<int:slide_id>/eliminar", methods=["POST"])
@login_required
def hero_slide_delete(slide_id):
    slide = HeroSlide.query.get_or_404(slide_id)
    db.session.delete(slide)
    db.session.commit()
    flash("Imagen eliminada de la galería.", "success")
    return redirect(url_for("admin.editar_contenido", section_key="hero"))


@admin_bp.route("/contenido/hero/slides/<int:slide_id>/mover", methods=["POST"])
@login_required
def hero_slide_move(slide_id):
    direction = request.form.get("direction", "up")
    slides = HeroSlide.query.order_by(HeroSlide.sort_order, HeroSlide.id).all()
    idx = next((i for i, s in enumerate(slides) if s.id == slide_id), None)
    if idx is None:
        flash("Imagen no encontrada.", "danger")
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
    flash("Imagen " + ("visible" if slide.active else "ocultada") + " en el sitio.", "success")
    return redirect(url_for("admin.editar_contenido", section_key="hero"))


@admin_bp.route("/contenido/hero/slides/<int:slide_id>/caption", methods=["POST"])
@login_required
def hero_slide_caption(slide_id):
    slide = HeroSlide.query.get_or_404(slide_id)
    slide.caption = request.form.get("caption", "").strip() or None
    db.session.commit()
    flash("Leyenda actualizada.", "success")
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
        flash(f"Se agregaron {added} imagen(es) a la galería Sobre nosotros.", "success")
    else:
        flash("No se pudo agregar ninguna imagen. Revisa formato y el límite de 10.", "warning")
    return redirect(url_for("admin.editar_contenido", section_key="about"))


@admin_bp.route("/contenido/about/slides/<int:slide_id>/eliminar", methods=["POST"])
@login_required
def about_slide_delete(slide_id):
    slide = AboutSlide.query.get_or_404(slide_id)
    db.session.delete(slide)
    db.session.commit()
    flash("Imagen eliminada de la galería.", "success")
    return redirect(url_for("admin.editar_contenido", section_key="about"))


@admin_bp.route("/contenido/about/slides/<int:slide_id>/mover", methods=["POST"])
@login_required
def about_slide_move(slide_id):
    direction = request.form.get("direction", "up")
    slides = AboutSlide.query.order_by(AboutSlide.sort_order, AboutSlide.id).all()
    idx = next((i for i, s in enumerate(slides) if s.id == slide_id), None)
    if idx is None:
        flash("Imagen no encontrada.", "danger")
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
    flash("Imagen " + ("visible" if slide.active else "ocultada") + " en el sitio.", "success")
    return redirect(url_for("admin.editar_contenido", section_key="about"))


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
    return render_template("admin/editar_servicio.html", servicio=None)


@admin_bp.route("/servicios/<int:service_id>/editar", methods=["GET", "POST"])
@login_required
def editar_servicio(service_id):
    servicio = Service.query.get_or_404(service_id)
    if request.method == "POST":
        return _guardar_servicio(servicio)
    return render_template("admin/editar_servicio.html", servicio=servicio)


def _guardar_servicio(servicio):
    slug = request.form.get("slug", "").strip().lower().replace(" ", "-")
    name = request.form.get("name", "").strip()
    short_description = request.form.get("short_description", "").strip()
    description = request.form.get("description", "").strip()
    order = request.form.get("order", 0)
    active = request.form.get("active") == "on"

    if not slug or not name:
        flash("El nombre y el slug son obligatorios.", "danger")
        return redirect(request.url)

    if servicio is None:
        servicio = Service()
        db.session.add(servicio)

    servicio.slug = slug
    servicio.name = name
    servicio.short_description = short_description
    servicio.description = description
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

    db.session.commit()
    flash(f'Servicio "{servicio.name}" guardado.', "success")
    return redirect(url_for("admin.servicios"))


@admin_bp.route("/servicios/<int:service_id>/eliminar", methods=["POST"])
@login_required
def eliminar_servicio(service_id):
    servicio = Service.query.get_or_404(service_id)
    db.session.delete(servicio)
    db.session.commit()
    flash("Servicio eliminado.", "success")
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
        flash("Configuración de correo actualizada.", "success")
        return redirect(url_for("admin.config_correo"))

    return render_template("admin/config_correo.html", settings=settings)


@admin_bp.route("/configuracion/correo/probar", methods=["POST"])
@login_required
def config_correo_probar():
    settings = EmailSettings.query.first()
    if not settings:
        flash("Primero guarda la configuración de correo.", "warning")
        return redirect(url_for("admin.config_correo"))

    ok, msg = send_test_email(settings)
    flash(
        f"Correo de prueba enviado a {settings.notify_email or settings.smtp_email}." if ok
        else f"No se pudo enviar el correo de prueba: {msg}",
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
        flash(f'Plantilla "{tpl.label}" actualizada.', "success")
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
            flash("No tienes permisos para acceder a esta sección.", "danger")
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
            flash("El usuario y la contraseña son obligatorios.", "danger")
            return redirect(url_for("admin.nuevo_usuario"))

        if Admin.query.filter_by(username=username).first():
            flash("Ya existe un usuario con ese nombre.", "danger")
            return redirect(url_for("admin.nuevo_usuario"))

        new_admin = Admin(username=username, is_superadmin=is_superadmin)
        new_admin.set_password(password)
        db.session.add(new_admin)
        db.session.commit()
        flash(f'Usuario "{username}" creado.', "success")
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
            flash("El usuario es obligatorio.", "danger")
            return redirect(url_for("admin.editar_usuario", user_id=user_id))

        existing = Admin.query.filter_by(username=new_username).first()
        if existing and existing.id != user_id:
            flash("Ya existe otro usuario con ese nombre.", "danger")
            return redirect(url_for("admin.editar_usuario", user_id=user_id))

        admin_user.username = new_username
        admin_user.is_superadmin = new_superadmin

        if new_password:
            admin_user.set_password(new_password)

        db.session.commit()
        flash(f'Usuario "{new_username}" actualizado.', "success")
        return redirect(url_for("admin.usuarios"))

    return render_template("admin/editar_usuario.html", admin_user=admin_user)


@admin_bp.route("/usuarios/<int:user_id>/eliminar", methods=["POST"])
@superadmin_required
def eliminar_usuario(user_id):
    admin_user = Admin.query.get_or_404(user_id)

    if admin_user.id == current_user.id:
        flash("No puedes eliminarte a ti mismo.", "danger")
        return redirect(url_for("admin.usuarios"))

    if admin_user.is_superadmin:
        superadmin_count = Admin.query.filter_by(is_superadmin=True).count()
        if superadmin_count <= 1:
            flash("No puedes eliminar el último superadmin.", "danger")
            return redirect(url_for("admin.usuarios"))

    db.session.delete(admin_user)
    db.session.commit()
    flash(f'Usuario "{admin_user.username}" eliminado.', "success")
    return redirect(url_for("admin.usuarios"))


@admin_bp.route("/usuarios/<int:user_id>/toggle-superadmin", methods=["POST"])
@superadmin_required
def toggle_superadmin(user_id):
    admin_user = Admin.query.get_or_404(user_id)

    if admin_user.id == current_user.id:
        flash("No puedes cambiar tu propio permiso de superadmin.", "danger")
        return redirect(url_for("admin.usuarios"))

    if admin_user.is_superadmin:
        superadmin_count = Admin.query.filter_by(is_superadmin=True).count()
        if superadmin_count <= 1:
            flash("No puedes quitar superadmin al último superadmin.", "danger")
            return redirect(url_for("admin.usuarios"))

    admin_user.is_superadmin = not admin_user.is_superadmin
    db.session.commit()

    estado = "otorgado" if admin_user.is_superadmin else "revocado"
    flash(f'Permiso de superadmin {estado} para "{admin_user.username}".', "success")
    return redirect(url_for("admin.usuarios"))
