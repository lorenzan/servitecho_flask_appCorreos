from datetime import datetime

from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import desc

from extensions import db
from models import Admin, Review, Quote, ContentBlock, Service, SocialLink, EmailSettings, EmailTemplate, AdsSettings
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
            flash("El nombre, el comentario y una calificación de 1 a 5 son obligatorios.", "danger")
            return redirect(request.url)

        review.name = name
        review.email = request.form.get("email", "").strip()
        review.rating = rating
        review.comment = comment
        review.approved = request.form.get("approved") == "on"
        db.session.commit()
        flash("Reseña actualizada.", "success")
        return redirect(url_for("admin.resenas"))

    return render_template("admin/editar_resena.html", review=review)


@admin_bp.route("/resenas/<int:review_id>/eliminar", methods=["POST"])
@login_required
def eliminar_resena(review_id):
    review = Review.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()
    flash("Reseña eliminada.", "success")
    return redirect(url_for("admin.resenas"))


# ---------- Redes sociales (pie de página) ----------

def _normalizar_url(url):
    url = url.strip()
    if url and not url.startswith(("http://", "https://", "mailto:", "tel:")):
        url = "https://" + url
    return url


@admin_bp.route("/redes")
@login_required
def redes_sociales():
    redes = SocialLink.query.order_by(SocialLink.order).all()
    return render_template("admin/redes_sociales.html", redes=redes)


@admin_bp.route("/redes/nueva", methods=["GET", "POST"])
@login_required
def nueva_red():
    if request.method == "POST":
        return _guardar_red(None)
    return render_template("admin/editar_red.html", red=None, plataformas=SocialLink.PLATFORM_LABELS)


@admin_bp.route("/redes/<int:link_id>/editar", methods=["GET", "POST"])
@login_required
def editar_red(link_id):
    red = SocialLink.query.get_or_404(link_id)
    if request.method == "POST":
        return _guardar_red(red)
    return render_template("admin/editar_red.html", red=red, plataformas=SocialLink.PLATFORM_LABELS)


def _guardar_red(red):
    name = request.form.get("name", "").strip()
    url = _normalizar_url(request.form.get("url", ""))
    platform = request.form.get("platform", "otro")
    if platform not in SocialLink.PLATFORMS:
        platform = "otro"
    try:
        order = int(request.form.get("order", 0))
    except (TypeError, ValueError):
        order = 0
    active = request.form.get("active") == "on"

    if not name or not url:
        flash("El nombre y el enlace (URL) son obligatorios.", "danger")
        return redirect(request.url)

    if red is None:
        red = SocialLink()
        db.session.add(red)

    red.name = name
    red.url = url
    red.platform = platform
    red.order = order
    red.active = active
    db.session.commit()
    flash(f'Red social "{red.name}" guardada.', "success")
    return redirect(url_for("admin.redes_sociales"))


@admin_bp.route("/redes/<int:link_id>/toggle", methods=["POST"])
@login_required
def toggle_red(link_id):
    red = SocialLink.query.get_or_404(link_id)
    red.active = not red.active
    db.session.commit()
    estado = "activada" if red.active else "desactivada"
    flash(f'Red social "{red.name}" {estado}.', "success")
    return redirect(url_for("admin.redes_sociales"))


@admin_bp.route("/redes/<int:link_id>/eliminar", methods=["POST"])
@login_required
def eliminar_red(link_id):
    red = SocialLink.query.get_or_404(link_id)
    db.session.delete(red)
    db.session.commit()
    flash(f'Red social "{red.name}" eliminada.', "success")
    return redirect(url_for("admin.redes_sociales"))


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

@admin_bp.route("/contenido")
@login_required
def contenido():
    blocks = ContentBlock.query.order_by(ContentBlock.label).all()
    return render_template("admin/contenido.html", blocks=blocks)


@admin_bp.route("/contenido/<section_key>", methods=["GET", "POST"])
@login_required
def editar_contenido(section_key):
    block = ContentBlock.query.filter_by(section_key=section_key).first_or_404()

    if request.method == "POST":
        if block.section_key != "logo":
            block.eyebrow = request.form.get("eyebrow", "").strip()
            block.title = request.form.get("title", "").strip()
            block.body = request.form.get("body", "").strip()
            block.extra = request.form.get("extra", "").strip()

        image = request.files.get("image")
        if image and image.filename:
            rel_path = save_upload(image, "content")
            if rel_path:
                block.image_path = rel_path

        db.session.commit()
        flash(f'Bloque "{block.label}" actualizado.', "success")
        return redirect(url_for("admin.contenido"))

    return render_template("admin/editar_contenido.html", block=block)


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
        flash("Configuración de Google Ads actualizada.", "success")
        return redirect(url_for("admin.config_marketing"))

    return render_template("admin/config_marketing.html", settings=settings)


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
