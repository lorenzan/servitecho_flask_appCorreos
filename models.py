from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db


class Admin(UserMixin, db.Model):
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_superadmin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class ContentBlock(db.Model):
    """Editable text/image blocks for the public site (managed from admin)."""
    __tablename__ = "content_blocks"

    id = db.Column(db.Integer, primary_key=True)
    section_key = db.Column(db.String(80), unique=True, nullable=False)
    label = db.Column(db.String(150), nullable=False)  # human-friendly label for admin UI
    eyebrow = db.Column(db.String(150))
    title = db.Column(db.String(300))
    body = db.Column(db.Text)
    image_path = db.Column(db.String(300))
    extra = db.Column(db.String(300))  # small extra field (phone, cta label, etc.)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Service(db.Model):
    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    short_description = db.Column(db.String(400))
    description = db.Column(db.Text)
    work_methods = db.Column(db.Text)  # métodos de trabajo: un ítem por línea
    image_path = db.Column(db.String(300))  # imagen de portada / fallback del hero
    video_path = db.Column(db.String(300))  # video opcional del hero (mp4/webm)
    order = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)

    gallery_images = db.relationship(
        "ServiceGalleryImage",
        backref="service",
        cascade="all, delete-orphan",
        lazy=True,
        order_by="ServiceGalleryImage.sort_order",
    )


class ServiceGalleryImage(db.Model):
    """Galería de fotos por servicio (editable desde el admin)."""
    __tablename__ = "service_gallery_images"

    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)
    image_path = db.Column(db.String(300), nullable=False)
    caption = db.Column(db.String(200))
    sort_order = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150))
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text, nullable=False)
    approved = db.Column(db.Boolean, default=True)  # published immediately; admin can always delete
    featured = db.Column(db.Boolean, default=False)  # aparece en el carrusel destacado
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Quote(db.Model):
    """Cotización: solicitud de presupuesto enviada por un cliente."""
    __tablename__ = "quotes"

    STATUS_CHOICES = ["pendiente", "en_revision", "cotizado", "rechazado"]
    STATUS_LABELS = {
        "pendiente": "Pending",
        "en_revision": "In review",
        "cotizado": "Quoted",
        "rechazado": "Rejected",
    }

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(40), nullable=False)
    email = db.Column(db.String(150))
    location = db.Column(db.String(250), nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    service_type = db.Column(db.String(150))
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="pendiente")
    admin_notes = db.Column(db.Text)
    client_response = db.Column(db.Text)
    responded_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    images = db.relationship(
        "QuoteImage", backref="quote", cascade="all, delete-orphan", lazy=True
    )

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, self.status)


class QuoteImage(db.Model):
    __tablename__ = "quote_images"

    id = db.Column(db.Integer, primary_key=True)
    quote_id = db.Column(db.Integer, db.ForeignKey("quotes.id"), nullable=False)
    image_path = db.Column(db.String(300), nullable=False)


class EmailSettings(db.Model):
    """Singleton row with SMTP credentials used to send notification emails."""
    __tablename__ = "email_settings"

    id = db.Column(db.Integer, primary_key=True)
    enabled = db.Column(db.Boolean, default=False)
    smtp_host = db.Column(db.String(120), default="smtp.gmail.com")
    smtp_port = db.Column(db.Integer, default=587)
    smtp_email = db.Column(db.String(150))
    smtp_app_password = db.Column(db.String(255))
    sender_name = db.Column(db.String(150), default="Tecuns Roofing")
    notify_email = db.Column(db.String(150))  # where admin notifications are sent
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EmailTemplate(db.Model):
    """Editable subject/body templates for outgoing notification emails."""
    __tablename__ = "email_templates"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    label = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(300), nullable=False)
    body = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AdsSettings(db.Model):
    """Singleton row: Google Ads / GA4 del sitio público (se gestiona desde admin).

    Arranca desactivado (enabled=False) — no formaba parte del alcance original.
    """
    __tablename__ = "ads_settings"

    id = db.Column(db.Integer, primary_key=True)
    enabled = db.Column(db.Boolean, default=False)
    google_ads_id = db.Column(db.String(120))  # ej. AW-XXXXXXXXX
    conversion_label = db.Column(db.String(120))  # etiqueta de conversión de Google Ads
    ga4_measurement_id = db.Column(db.String(120))  # opcional, ej. G-XXXXXXXXX
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HeroSlide(db.Model):
    """Imágenes del carrusel de la portada (editables desde el admin)."""
    __tablename__ = "hero_slides"

    id = db.Column(db.Integer, primary_key=True)
    image_path = db.Column(db.String(300), nullable=False)
    caption = db.Column(db.String(200))  # texto opcional sobre la imagen
    sort_order = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AboutSlide(db.Model):
    """Imágenes de la galería 3D del bloque Sobre nosotros."""
    __tablename__ = "about_slides"

    id = db.Column(db.Integer, primary_key=True)
    image_path = db.Column(db.String(300), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class QuoteGlassCard(db.Model):
    """Cards de cristal (imágenes) del hero de cotización — editables en admin."""
    __tablename__ = "quote_glass_cards"

    id = db.Column(db.Integer, primary_key=True)
    image_path = db.Column(db.String(300), nullable=False)
    caption = db.Column(db.String(80))  # texto en la base de la card (data-text)
    sort_order = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ReviewStackCard(db.Model):
    """Cards apiladas del hero de reseñas — editables en admin."""
    __tablename__ = "review_stack_cards"

    id = db.Column(db.Integer, primary_key=True)
    image_path = db.Column(db.String(300), nullable=False)
    caption = db.Column(db.String(80))  # título del panel al hover
    button_label = db.Column(db.String(40))  # texto del botón en el panel
    sort_order = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TrustCard(db.Model):
    """Highlight cards in the 'What sets us apart' section (editable from admin)."""
    __tablename__ = "trust_cards"

    ICON_CHOICES = ("shield", "support", "install", "systems")

    id = db.Column(db.Integer, primary_key=True)
    metric = db.Column(db.String(40), nullable=False)  # e.g. +30, 24/7, 100%
    title = db.Column(db.String(150), nullable=False)
    body = db.Column(db.String(400))
    icon_key = db.Column(db.String(40), default="shield")  # built-in coin SVG
    image_path = db.Column(db.String(300))  # optional custom icon image
    sort_order = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
