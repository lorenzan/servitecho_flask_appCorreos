"""Ejecutar una vez para poblar la base de datos con datos iniciales:
    python seed.py
"""
from app import create_app
from extensions import db
from models import Admin, ContentBlock, Service, Review, SocialLink, EmailSettings, EmailTemplate

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
        label="Portada (Hero)",
        eyebrow="Construyendo confianza en cada proyecto",
        title="Techos, Fachadas y Módulos Prefabricados en El Salvador",
        body="Diseño, suministro e instalación de sistemas de techos metálicos, "
        "fachadas y soluciones modulares, con garantía y respaldo profesional.",
        extra="Solicita tu cotización",
        image_path=None,
    ),
    dict(
        section_key="about",
        label="Sobre nosotros",
        eyebrow="Acerca de nosotros",
        title="Construimos Confianza",
        body="En Servitecho nos especializamos en el diseño, fabricación e instalación "
        "de sistemas de techos metálicos, fachadas, paneles termoacústicos y soluciones "
        "modulares. Nuestro compromiso es desarrollar proyectos con los más altos "
        "estándares de calidad, ofreciendo soluciones eficientes, duraderas y adaptadas "
        "a las necesidades de cada cliente.\n\nTrabajamos con un equipo altamente "
        "capacitado, materiales de primera calidad y procesos que garantizan seguridad, "
        "cumplimiento y excelencia en cada obra, ya sea residencial, comercial o industrial.",
        extra="Calidad, Compromiso, Puntualidad, Responsabilidad, Innovación, Confianza",
        image_path=None,
    ),
    dict(
        section_key="mission",
        label="Misión",
        eyebrow=None,
        title="Misión",
        body="Brindar soluciones innovadoras en techos y fachadas con productos de alta "
        "calidad y un servicio que supere las expectativas de nuestros clientes.",
        extra=None,
        image_path=None,
    ),
    dict(
        section_key="vision",
        label="Visión",
        eyebrow=None,
        title="Visión",
        body="Ser la empresa líder en el diseño, fabricación e instalación de sistemas "
        "de techos y fachadas metálicas, reconocida por su innovación, calidad y "
        "excelencia.",
        extra=None,
        image_path=None,
    ),
    dict(
        section_key="support",
        label="Soporte 24/7",
        eyebrow=None,
        title="Soporte 24/7",
        body="Nuestro equipo está disponible las 24 horas del día, los 7 días de la "
        "semana, para brindar atención oportuna y soporte a nuestros clientes cuando "
        "más lo necesitan.",
        extra="2289-9258",
        image_path=None,
    ),
    dict(
        section_key="why_us",
        label="Qué nos distingue",
        eyebrow="Nuestro compromiso",
        title="¿Qué nos distingue?",
        body="Más que instalar techos, construimos soluciones duraderas. Combinamos "
        "ingeniería, materiales de alta calidad y mano de obra especializada para "
        "entregar proyectos seguros, eficientes y con acabados de excelencia. Nuestro "
        "compromiso es cumplir los tiempos establecidos y brindar un servicio confiable "
        "antes, durante y después de cada proyecto.",
        extra="Cotiza tu proyecto",
        image_path=None,
    ),
    dict(
        section_key="site_info",
        label="Datos de contacto (encabezado y pie de página)",
        eyebrow="6956-1628",  # phone / whatsapp
        title="info@servitecho.com.sv",  # email
        body="Jardines de Cuscatlán, Pol F #25 | Antiguo Cuscatlán, La Libertad",  # address
        extra="Lun - Vie (8AM - 6PM)",  # hours
        image_path=None,
    ),
]

SERVICES = [
    dict(
        slug="standing-seam",
        name="Standing Seam",
        short_description="Sistema de techo metálico con fijación oculta, sin "
        "perforaciones expuestas y acabado arquitectónico moderno.",
        description="Nuestros techos Standing Seam utilizan un sistema de fijación "
        "oculta que elimina perforaciones expuestas, reduce el riesgo de filtraciones "
        "y ofrece un acabado arquitectónico moderno con máxima durabilidad. Ideal para "
        "proyectos comerciales e industriales que buscan un sistema de techo de alto "
        "desempeño y garantía de larga duración.",
        order=1,
    ),
    dict(
        slug="panel-termoacustico",
        name="Panel Termoacústico",
        short_description="Panel tipo sándwich con núcleo de poliuretano de alta "
        "densidad para aislamiento térmico y acústico.",
        description="Sistema de panel aislado diseñado para ofrecer aislamiento "
        "térmico y acústico, reduciendo la transferencia de calor y el ruido. Ideal "
        "para naves industriales, bodegas, oficinas, centros comerciales y proyectos "
        "que requieren eficiencia energética y un acabado moderno.",
        order=2,
    ),
    dict(
        slug="modulos-constructivos",
        name="Módulos Constructivos",
        short_description="Espacios prefabricados y desmontables para oficinas, "
        "bodegas y campamentos.",
        description="Solución constructiva de creación y ensamble de módulos que "
        "permiten crear espacios únicos de diseño para construcciones u oficinas, con "
        "la facilidad de trasladar, ampliar o desarmar la estructura según las "
        "necesidades de cada proyecto.",
        order=3,
    ),
]

SAMPLE_REVIEWS = [
    dict(name="Carlos Menéndez", rating=5,
         comment="Excelente trabajo instalando el techo Standing Seam en nuestra "
         "bodega. Cumplieron los tiempos y la calidad fue impecable.", approved=True),
    dict(name="Ana Guevara", rating=5,
         comment="El panel termoacústico bajó muchísimo la temperatura dentro de la "
         "nave industrial. Muy buen servicio y asesoría desde la cotización.",
         approved=True),
    dict(name="Roberto Alas", rating=4,
         comment="Buena atención y materiales de calidad. El módulo constructivo que "
         "instalaron para nuestra oficina quedó muy bien.", approved=True),
]


EMAIL_TEMPLATES = [
    dict(
        key="nueva_resena",
        label="Notificación: nueva reseña",
        subject="⭐ Nueva reseña recibida — {{ nombre }}",
        body=(
            "Hola,\n\n"
            "Se recibió una nueva reseña en el sitio web de Servitecho.\n\n"
            "Cliente: {{ nombre }}\n"
            "Correo: {{ email }}\n"
            "Calificación: {{ calificacion }} / 5\n"
            "Comentario:\n{{ comentario }}\n\n"
            "Fecha: {{ fecha }}\n\n"
            "Puedes revisarla u ocultarla desde el panel de administración:\n{{ enlace_admin }}"
        ),
    ),
    dict(
        key="nueva_cotizacion",
        label="Notificación: nueva cotización",
        subject="📋 Nueva solicitud de cotización — {{ nombre }}",
        body=(
            "Hola,\n\n"
            "Se recibió una nueva solicitud de cotización.\n\n"
            "Cliente: {{ nombre }}\n"
            "Teléfono: {{ telefono }}\n"
            "Correo: {{ email }}\n"
            "Ubicación: {{ ubicacion }}\n"
            "Producto de interés: {{ producto }}\n\n"
            "Descripción del proyecto:\n{{ descripcion }}\n\n"
            "Fecha: {{ fecha }}\n\n"
            "Revisa la solicitud completa y las fotos adjuntas aquí:\n{{ enlace_admin }}"
        ),
    ),
    dict(
        key="respuesta_cotizacion",
        label="Respuesta de cotización (al cliente)",
        subject="Respuesta a tu solicitud de cotización — Servitecho",
        body=(
            "Hola {{ nombre }},\n\n"
            "Gracias por contactar a Servitecho. Aquí tienes la respuesta a tu solicitud de "
            "cotización para el proyecto en {{ ubicacion }}:\n\n"
            "{{ respuesta }}\n\n"
            "Estado actual de tu solicitud: {{ estado }}\n\n"
            "Si tienes alguna pregunta, no dudes en responder este correo o escribirnos.\n\n"
            "Saludos,\nEquipo Servitecho"
        ),
    ),
]


DEFAULT_SOCIAL_LINKS = [
    dict(platform="facebook", name="Facebook", url="", active=False, order=1),
    dict(platform="instagram", name="Instagram", url="", active=False, order=2),
    dict(platform="whatsapp", name="WhatsApp", url="", active=False, order=3),
]


def run():
    with app.app_context():
        db.create_all()

        if not Admin.query.filter_by(username="admin").first():
            admin = Admin(username="admin", is_superadmin=True)
            admin.set_password("Servitecho2024!")
            db.session.add(admin)
            print("Admin creado -> usuario: admin / contraseña: Servitecho2024!")
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

        if SocialLink.query.count() == 0:
            for data in DEFAULT_SOCIAL_LINKS:
                db.session.add(SocialLink(**data))
            print(f"Redes sociales por defecto creadas ({len(DEFAULT_SOCIAL_LINKS)}).")

        if not EmailSettings.query.first():
            db.session.add(EmailSettings(smtp_host="smtp.gmail.com", smtp_port=587, enabled=False))
            print("Configuración de correo inicializada (desactivada por defecto).")

        for data in EMAIL_TEMPLATES:
            if not EmailTemplate.query.filter_by(key=data["key"]).first():
                db.session.add(EmailTemplate(**data))
        print(f"Plantillas de correo listas ({len(EMAIL_TEMPLATES)}).")

        db.session.commit()
        print("Base de datos inicializada correctamente.")


if __name__ == "__main__":
    run()
