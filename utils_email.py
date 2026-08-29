import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import render_template_string, url_for

from models import EmailSettings, EmailTemplate

TEMPLATE_PLACEHOLDERS = {
    "nueva_resena": ["nombre", "email", "calificacion", "comentario", "fecha", "enlace_admin"],
    "nueva_cotizacion": [
        "nombre", "telefono", "email", "ubicacion", "producto",
        "descripcion", "fecha", "enlace_admin",
    ],
    "respuesta_cotizacion": [
        "nombre", "ubicacion", "producto", "descripcion", "estado", "respuesta",
    ],
}


def get_settings():
    return EmailSettings.query.first()


def get_template(key):
    return EmailTemplate.query.filter_by(key=key).first()


def _render(text, context):
    if not text:
        return ""
    try:
        return render_template_string(text, **context)
    except Exception:
        return text


def send_email(to_addr, subject, body, settings=None):
    """Low-level SMTP send. Returns (ok: bool, message: str)."""
    settings = settings or get_settings()
    if not settings or not settings.enabled:
        return False, "El envío de correos está desactivado en Configuración de correo."
    if not settings.smtp_email or not settings.smtp_app_password:
        return False, "Faltan las credenciales SMTP (correo o contraseña de aplicación)."
    if not to_addr:
        return False, "No hay una dirección de correo destino."

    try:
        msg = MIMEMultipart()
        msg["From"] = f"{settings.sender_name or 'Tecuns Roofing'} <{settings.smtp_email}>"
        msg["To"] = to_addr
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(settings.smtp_host or "smtp.gmail.com", settings.smtp_port or 587, timeout=15) as server:
            server.starttls()
            server.login(settings.smtp_email, settings.smtp_app_password)
            server.sendmail(settings.smtp_email, [to_addr], msg.as_string())
        return True, "Correo enviado correctamente."
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def notify_new_review(review):
    """Best-effort notification to the admin when a review is submitted."""
    try:
        settings = get_settings()
        if not settings or not settings.enabled or not settings.notify_email:
            return
        tpl = get_template("nueva_resena")
        if not tpl:
            return
        context = {
            "nombre": review.name,
            "email": review.email or "—",
            "calificacion": review.rating,
            "comentario": review.comment,
            "fecha": review.created_at.strftime("%d/%m/%Y %H:%M") if review.created_at else "",
            "enlace_admin": url_for("admin.resenas", _external=True),
        }
        subject = _render(tpl.subject, context)
        body = _render(tpl.body, context)
        send_email(settings.notify_email, subject, body, settings)
    except Exception:
        pass


def notify_new_quote(quote):
    """Best-effort notification to the admin when a quote request is submitted."""
    try:
        settings = get_settings()
        if not settings or not settings.enabled or not settings.notify_email:
            return
        tpl = get_template("nueva_cotizacion")
        if not tpl:
            return
        context = {
            "nombre": quote.name,
            "telefono": quote.phone,
            "email": quote.email or "—",
            "ubicacion": quote.location,
            "producto": quote.service_type or "—",
            "descripcion": quote.description,
            "fecha": quote.created_at.strftime("%d/%m/%Y %H:%M") if quote.created_at else "",
            "enlace_admin": url_for("admin.cotizacion_detalle", quote_id=quote.id, _external=True),
        }
        subject = _render(tpl.subject, context)
        body = _render(tpl.body, context)
        send_email(settings.notify_email, subject, body, settings)
    except Exception:
        pass


def send_quote_response(quote):
    """Send the admin's written response for a quote to the client's email.
    Returns (ok: bool, message: str)."""
    settings = get_settings()
    if not settings or not settings.enabled:
        return False, "El envío de correos está desactivado en Configuración de correo."
    if not quote.email:
        return False, "El cliente no proporcionó un correo electrónico."
    tpl = get_template("respuesta_cotizacion")
    if not tpl:
        return False, "No existe la plantilla de respuesta de cotización."

    context = {
        "nombre": quote.name,
        "ubicacion": quote.location,
        "producto": quote.service_type or "—",
        "descripcion": quote.description,
        "estado": quote.status.replace("_", " "),
        "respuesta": quote.client_response or "",
    }
    subject = _render(tpl.subject, context)
    body = _render(tpl.body, context)
    return send_email(quote.email, subject, body, settings)


def send_test_email(settings):
    return send_email(
        settings.notify_email or settings.smtp_email,
        "Test email — Tecuns Roofing",
        "This is a test email sent from the Tecuns Roofing admin panel. "
        "If you received it, the email configuration is working correctly.",
        settings,
    )
