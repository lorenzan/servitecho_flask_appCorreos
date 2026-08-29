"""Ejecutar una vez para poblar la base de datos con datos iniciales:
    python seed.py
"""
from app import create_app
from extensions import db
from models import Admin, ContentBlock, Service, Review, EmailSettings, EmailTemplate, AdsSettings

app = create_app()

CONTENT_BLOCKS = [
    dict(
        section_key="logo",
        label="Logotipo",
        eyebrow=None,
        title=None,
        body=None,
        extra=None,
        image_path=None,
    ),
    dict(
        section_key="hero",
        label="Homepage (Hero)",
        eyebrow="Building trust in every project",
        title="Roofs, Facades and Prefabricated Modules in El Salvador",
        body="Design, supply and installation of industrial roofs, metal facades "
        "and prefabricated modules in El Salvador.",
        extra="Request your quote",
        image_path=None,
    ),
    dict(
        section_key="about",
        label="About Us",
        eyebrow="About Us",
        title="We Build Trust",
        body="At Tecuns Roofing we specialize in the design, manufacturing and installation "
        "of metal roofing systems, facades, thermoacoustic panels and modular "
        "solutions. Our commitment is to develop projects with the highest "
        "quality standards, offering efficient, durable solutions adapted "
        "to each client's needs.\n\nWe work with a highly "
        "skilled team, first-quality materials and processes that guarantee safety, "
        "compliance and excellence in every project, whether residential, commercial or industrial.",
        extra="Quality, Commitment, Punctuality, Responsibility, Innovation, Trust",
        image_path=None,
    ),
    dict(
        section_key="mission",
        label="Mission",
        eyebrow=None,
        title="Mission",
        body="Provide innovative roofing and facade solutions with high-quality "
        "products and service that exceeds our clients' expectations.",
        extra=None,
        image_path=None,
    ),
    dict(
        section_key="vision",
        label="Vision",
        eyebrow=None,
        title="Vision",
        body="Be the leading company in the design, manufacturing and installation of "
        "metal roofing and facade systems, recognized for innovation, quality and "
        "excellence.",
        extra=None,
        image_path=None,
    ),
    dict(
        section_key="support",
        label="24/7 Support",
        eyebrow=None,
        title="24/7 Support",
        body="Our team is available 24 hours a day, 7 days a week, "
        "to provide timely attention and support to our clients when "
        "they need it most.",
        extra="2289-9258",
        image_path=None,
    ),
    dict(
        section_key="why_us",
        label="What Sets Us Apart",
        eyebrow="Our Commitment",
        title="What Sets Us Apart?",
        body="More than installing roofs, we build lasting solutions. We combine "
        "engineering, high-quality materials and specialized labor to "
        "deliver safe, efficient projects with excellent finishes. Our "
        "commitment is to meet established timelines and provide reliable service "
        "before, during and after every project.",
        extra="Quote your project",
        image_path=None,
    ),
    dict(
        section_key="site_info",
        label="Contact Info (Header & Footer)",
        eyebrow="6956-1628",  # phone / whatsapp
        title="info@tecunsroofing.com",  # email
        body="Jardines de Cuscatlán, Pol F #25 | Antiguo Cuscatlán, La Libertad",  # address
        extra="Mon - Fri (8AM - 6PM)",  # hours
        image_path="",  # secondary phone (optional)
    ),
    dict(
        section_key="socials",
        label="Social Media (Footer)",
        eyebrow="",  # WhatsApp URL (empty = built from phone)
        title="",  # Facebook URL
        body="",  # Instagram URL
        extra="",  # TikTok URL
        image_path=None,
    ),
    dict(
        section_key="cotizacion",
        label="Quote (Glass Cards)",
        eyebrow="Quote",
        title="Tell us about your project",
        body="Give us the location, describe what you need and upload site photos. "
        "Our team will review your request and contact you with a proposal.",
        extra="No obligation · Quick response · Custom projects",
        image_path=None,
    ),
    dict(
        section_key="resenas",
        label="Reviews (Stacked Cards)",
        eyebrow="Reviews",
        title="Our customers' experience",
        body="Completed projects, real opinions. Share yours too.",
        extra="",
        image_path=None,
    ),
]

SERVICES = [
    dict(
        slug="standing-seam",
        name="Standing Seam",
        short_description="Metal roofing system with concealed fastening, no "
        "exposed penetrations and modern architectural finish.",
        description="Our Standing Seam roofs use a concealed fastening "
        "system that eliminates exposed penetrations, reduces leak risk "
        "and provides a modern architectural finish with maximum durability. Ideal for "
        "commercial and industrial projects seeking a high-performance "
        "roofing system with long-term warranty.",
        order=1,
    ),
    dict(
        slug="panel-termoacustico",
        name="Thermoacoustic Panel",
        short_description="Sandwich-type panel with high-density polyurethane core "
        "for thermal and acoustic insulation.",
        description="Insulated panel system designed to provide thermal "
        "and acoustic insulation, reducing heat transfer and noise. Ideal "
        "for industrial warehouses, storage facilities, offices, shopping centers and projects "
        "requiring energy efficiency and a modern finish.",
        order=2,
    ),
    dict(
        slug="modulos-constructivos",
        name="Constructive Modules",
        short_description="Prefabricated and demountable spaces for offices, "
        "warehouses and camps.",
        description="Constructive solution for creating and assembling modules that "
        "allow creating unique design spaces for buildings or offices, with "
        "the flexibility to relocate, expand or disassemble the structure according to "
        "each project's needs.",
        order=3,
    ),
]

SAMPLE_REVIEWS = [
    dict(name="Carlos Menéndez", rating=5,
         comment="Excellent work installing the Standing Seam roof in our "
         "warehouse. They met the deadlines and the quality was impeccable.", approved=True),
    dict(name="Ana Guevara", rating=5,
         comment="The thermoacoustic panel greatly reduced the temperature inside the "
         "industrial building. Very good service and advice from the quote.",
         approved=True),
    dict(name="Roberto Alas", rating=4,
         comment="Good attention and quality materials. The constructive module they "
         "installed for our office turned out very well.", approved=True),
]


EMAIL_TEMPLATES = [
    dict(
        key="nueva_resena",
        label="Notification: new review",
        subject="⭐ New review received — {{ nombre }}",
        body=(
            "Hello,\n\n"
            "A new review was received on the Tecuns Roofing website.\n\n"
            "Client: {{ nombre }}\n"
            "Email: {{ email }}\n"
            "Rating: {{ calificacion }} / 5\n"
            "Comment:\n{{ comentario }}\n\n"
            "Date: {{ fecha }}\n\n"
            "You can review or hide it from the admin panel:\n{{ enlace_admin }}"
        ),
    ),
    dict(
        key="nueva_cotizacion",
        label="Notification: new quote request",
        subject="📋 New quote request — {{ nombre }}",
        body=(
            "Hello,\n\n"
            "A new quote request was received.\n\n"
            "Client: {{ nombre }}\n"
            "Phone: {{ telefono }}\n"
            "Email: {{ email }}\n"
            "Location: {{ ubicacion }}\n"
            "Product of interest: {{ producto }}\n\n"
            "Project description:\n{{ descripcion }}\n\n"
            "Date: {{ fecha }}\n\n"
            "Review the full request and attached photos here:\n{{ enlace_admin }}"
        ),
    ),
    dict(
        key="respuesta_cotizacion",
        label="Quote response (to client)",
        subject="Response to your quote request — Tecuns Roofing",
        body=(
            "Hello {{ nombre }},\n\n"
            "Thank you for contacting Tecuns Roofing. Here is the response to your quote "
            "request for the project at {{ ubicacion }}:\n\n"
            "{{ respuesta }}\n\n"
            "Current status of your request: {{ estado }}\n\n"
            "If you have any questions, feel free to reply to this email or contact us.\n\n"
            "Best regards,\nTecuns Roofing Team"
        ),
    ),
]


def _rebrand_text(value):
    if not value or not isinstance(value, str):
        return value
    text = value
    for old, new in (
        ("Servitecho El Salvador", "Tecuns Roofing"),
        ("Equipo Servitecho", "Equipo Tecuns Roofing"),
        ("info@servitecho.com.sv", "info@tecunsroofing.com"),
        ("admin@servitecho.com.sv", "admin@tecunsroofing.com"),
        ("Servitecho", "Tecuns Roofing"),
        ("servitecho.com.sv", "tecunsroofing.com"),
    ):
        text = text.replace(old, new)
    return text


def _sync_branding():
    """Actualiza textos de marca en registros ya existentes (Servitecho → Tecuns Roofing)."""
    updated = 0

    for data in CONTENT_BLOCKS:
        block = ContentBlock.query.filter_by(section_key=data["section_key"]).first()
        if not block:
            continue
        changed = False
        for field in ("eyebrow", "title", "body", "extra"):
            desired = data.get(field)
            current = getattr(block, field)
            if desired is None:
                continue
            # Solo reescribe si el valor actual aún menciona Servitecho,
            # o si es un campo de marca que debe quedar alineado al seed.
            if current and "Servitecho" in str(current):
                setattr(block, field, desired)
                changed = True
            elif data["section_key"] in {"about", "site_info"} and current != desired:
                # about/site_info llevan el nombre de marca
                if field in {"body", "title"} and (
                    (current and "Servitecho" in str(current))
                    or data["section_key"] == "site_info" and field == "title"
                    or data["section_key"] == "about" and field == "body"
                ):
                    setattr(block, field, desired)
                    changed = True
        if changed:
            updated += 1

    for data in EMAIL_TEMPLATES:
        tpl = EmailTemplate.query.filter_by(key=data["key"]).first()
        if not tpl:
            continue
        changed = False
        for field in ("subject", "body", "label"):
            current = getattr(tpl, field)
            desired = data.get(field)
            if current and ("Servitecho" in str(current) or "servitecho" in str(current).lower()):
                setattr(tpl, field, desired)
                changed = True
        if changed:
            updated += 1

    settings = EmailSettings.query.first()
    if settings:
        if settings.sender_name and "Servitecho" in settings.sender_name:
            settings.sender_name = "Tecuns Roofing"
            updated += 1
        if settings.notify_email and "servitecho" in settings.notify_email.lower():
            settings.notify_email = _rebrand_text(settings.notify_email)
            updated += 1
        if settings.smtp_email and "servitecho" in settings.smtp_email.lower():
            settings.smtp_email = _rebrand_text(settings.smtp_email)
            updated += 1

    return updated


def run():
    with app.app_context():
        db.create_all()

        if not Admin.query.filter_by(username="admin").first():
            admin = Admin(username="admin", is_superadmin=True)
            admin.set_password("Tecuns2024!")
            db.session.add(admin)
            print("Admin creado -> usuario: admin / contraseña: Tecuns2024!")
        else:
            print("Admin ya existe, se omite.")

        for data in CONTENT_BLOCKS:
            if not ContentBlock.query.filter_by(section_key=data["section_key"]).first():
                db.session.add(ContentBlock(**data))
        print(f"Bloques de contenido listos ({len(CONTENT_BLOCKS)}).")

        for data in SERVICES:
            if not Service.query.filter_by(slug=data["slug"]).first():
                db.session.add(Service(**data))
        print(f"Servicios listos ({len(SERVICES)}).")

        if Review.query.count() == 0:
            for data in SAMPLE_REVIEWS:
                db.session.add(Review(**data))
            print(f"Reseñas de ejemplo creadas ({len(SAMPLE_REVIEWS)}).")

        if not EmailSettings.query.first():
            db.session.add(EmailSettings(
                smtp_host="smtp.gmail.com",
                smtp_port=587,
                enabled=False,
                sender_name="Tecuns Roofing",
            ))
            print("Configuración de correo inicializada (desactivada por defecto).")

        for data in EMAIL_TEMPLATES:
            if not EmailTemplate.query.filter_by(key=data["key"]).first():
                db.session.add(EmailTemplate(**data))
        print(f"Plantillas de correo listas ({len(EMAIL_TEMPLATES)}).")

        if not AdsSettings.query.first():
            db.session.add(AdsSettings(enabled=False, google_ads_id="", conversion_label="", ga4_measurement_id=""))
            print("Configuración de Google Ads inicializada (desactivada por defecto).")

        brand_updates = _sync_branding()
        if brand_updates:
            print(f"Marca actualizada en {brand_updates} registro(s) existente(s) (Servitecho -> Tecuns Roofing).")

        db.session.commit()
        print("Base de datos inicializada correctamente.")


if __name__ == "__main__":
    run()
