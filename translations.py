"""Traducción automática del sitio con deep-translator.

El contenido se redacta en español. Cuando el visitante elige inglés (o lo
detectamos automáticamente) traducimos con deep-translator (Google) y
guardamos el resultado en caché —en memoria y en un archivo JSON— para no
repetir llamadas a la red y que las siguientes visitas sean instantáneas.

Uso:
  - Textos fijos en templates:   {{ t('Texto en español') }}
  - Objetos de BD:               localize(obj, campos)  -> proxy que traduce
                                  los atributos indicados al renderizar
  - Idioma activo:               g.lang  ('es' | 'en')
"""
import json
import os
import threading

from flask import g, request

try:
    from deep_translator import GoogleTranslator
except Exception:  # pragma: no cover — deep-translator no instalado
    GoogleTranslator = None

ES = "es"
EN = "en"
SUPPORTED = (ES, EN)
DEFAULT = ES

# Qué campos de cada bloque de contenido se traducen (el resto, como
# image_path o extra= teléfono, se deja igual).
BLOCK_FIELDS = {
    "hero": ["eyebrow", "title", "body", "extra"],
    "about": ["eyebrow", "title", "body", "extra"],
    "mission": ["eyebrow", "title", "body"],
    "vision": ["eyebrow", "title", "body"],
    "values": ["eyebrow", "title", "body"],
    "support": ["eyebrow", "title", "body"],
    "why_us": ["eyebrow", "title", "body"],
}
SERVICE_FIELDS = ("name", "short_description", "description")
REVIEW_FIELDS = ("comment",)

# Textos fijos de los templates públicos. Se precargan al arrancar para que
# el primer visitante en inglés no espere a que se traduzcan uno por uno.
_STATIC_STRINGS = [
    # Navegación
    "Inicio", "Reseñas", "Cotización", "Solicita tu cotización",
    "Solicitar cotización", "Solicitar Cotización", "Llámenos Hoy",
    "Expertos en techos residenciales y comerciales",
    "Ver productos", "Ver detalles",
    "Ver todas / dejar reseña", "Dejar una reseña", "Volver al inicio",
    "Ver reseñas", "Acceso administrador", "Servicios", "Contacto", "Redes sociales",
    "Todos los derechos reservados.",
    # Inicio
    "Techos, Fachadas y Módulos Prefabricados",
    "Techos, Fachadas y Módulos Prefabricados en El Salvador",
    "Diseño, suministro e instalación de techos industriales, fachadas "
    "metálicas y módulos prefabricados en El Salvador.",
    "Construyendo confianza en cada proyecto",
    "Productos", "Sistemas para cada tipo de proyecto",
    "Fabricación, suministro e instalación con garantía para proyectos "
    "residenciales, comerciales e industriales.",
    "Nuestro compromiso", "¿Qué nos distingue?",
    "Años de garantía Standing Seam", "Soporte a clientes",
    "Instalación profesional", "Sistemas constructivos",
    "Más de 5 años de experiencia", "Años de experiencia", "Años de", "experiencia",
    "Sello de calidad profesional en techos residenciales y comerciales",
    "Protección duradera con sistemas de techo certificados y respaldo real.",
    "Atención continua para emergencias, mantenimiento y seguimiento de obra.",
    "Cuadrillas especializadas, acabados impecables y seguridad en cada proyecto.",
    "Standing Seam, paneles termoacústicos y módulos adaptados a cada obra.",
    "Galería de proyectos",
    "Acerca de nosotros", "Construimos Confianza", "Nuestros valores",
    "Misión", "Visión", "Soporte 24/7", "Llamar:",
    "Servicios", "Contacto", "Redes sociales", "Síguenos y contáctanos",
    "Dejar una reseña", "Todos los derechos reservados.", "Acceso administrador",
    "Cliente Tecuns", "estrellas",
    "Aún no hay reseñas publicadas. ¡Sé el primero en compartir tu experiencia!",
    "¿Listo para construir tu próximo proyecto?",
    "Sin compromiso · Respuesta rápida · Proyectos a medida",
    "Cuéntanos la ubicación, lo que necesitas y sube fotos del sitio. "
    "Te enviamos tu cotización sin compromiso.",
    # Reseñas
    "Reseñas de clientes", "La experiencia de nuestros clientes",
    "Proyectos entregados, opiniones reales. Comparte también la tuya.",
    "Opiniones publicadas", "Deja tu reseña",
    "Tu reseña se publicará luego de ser revisada por nuestro equipo.",
    "Nombre", "Correo (opcional)", "Calificación", "Comentario",
    "Cuéntanos sobre tu proyecto y experiencia con Servitecho...",
    "Enviar reseña",
    # Cotización
    "Cuéntanos sobre tu proyecto",
    "Danos la ubicación, describe lo que necesitas y sube fotos del sitio. "
    "Nuestro equipo revisará tu solicitud y te contactará con una propuesta.",
    "Nombre completo", "Teléfono / WhatsApp", "Producto de interés",
    "Selecciona una opción", "Otro / No estoy seguro",
    "Ubicación del proyecto",
    "Departamento, municipio, dirección o punto de referencia",
    "Escribe la dirección o usa el mapa de abajo para marcar el punto "
    "exacto — se autocompletará.",
    "Marca la ubicación en el mapa (opcional)",
    "Usar mi ubicación actual", "Buscar dirección, colonia o ciudad...",
    "Aún no has marcado un punto — el mapa está centrado en El Salvador. "
    "Haz clic para colocar el pin.",
    "Describe lo que necesitas",
    "Tipo de techo o fachada, dimensiones aproximadas, estado actual, plazos, etc.",
    "Fotos del sitio (opcional, hasta 6 imágenes)",
    "Sube fotos del techo, fachada o área del proyecto — nos ayuda a "
    "preparar una cotización más precisa.",
    "Enviar solicitud de cotización",
    # Detalle de servicio
    "Producto", "Descripción técnica", "Sobre este sistema",
    "Cotiza este producto", "Otros productos",
    # Gracias
    "Solicitud enviada", "Solicitud recibida",
    "¡Gracias! Tu solicitud fue enviada",
    "Nuestro equipo revisará la información y las fotos de tu proyecto, y "
    "te contactaremos pronto con tu cotización.",
    # Error 404 / 500
    "Error", "Página no encontrada",
    "Lo sentimos, la página que buscas no existe o fue movida.",
    "Algo salió mal",
    "Ocurrió un error inesperado. Inténtalo de nuevo en unos minutos.",
]

_cache = {}
_cache_lock = threading.Lock()
_MAX_CACHE = 6000
_cache_file = None  # se define en init_app()


def init_app(app):
    """Configura la caché persistente y precarga las traducciones en segundo plano."""
    global _cache_file
    _cache_file = os.path.join(app.instance_path, "translation_cache.json")
    _load_cache()
    if _enabled():
        thread = threading.Thread(
            target=_prewarm, args=(app,), name="translation-prewarm", daemon=True
        )
        thread.start()


def _load_cache():
    global _cache
    try:
        with open(_cache_file, encoding="utf-8") as fh:
            _cache = json.load(fh)
    except Exception:
        _cache = {}


def _save_cache():
    try:
        with open(_cache_file, "w", encoding="utf-8") as fh:
            json.dump(_cache, fh, ensure_ascii=False)
    except Exception:
        pass


def set_language():
    """before_request: idioma activo = cookie del usuario > Accept-Language."""
    lang = request.cookies.get("lang")
    if lang not in SUPPORTED:
        lang = detect_lang()
    g.lang = lang


def detect_lang():
    """Detecta el idioma por el encabezado Accept-Language del navegador.

    Un visitante en USA normalmente envía 'en-US...' (→ inglés); en LATAM
    'es-*' (→ español). El selector manual siempre tiene prioridad.
    """
    accept = request.headers.get("Accept-Language", "")
    primary = accept.split(",")[0].strip().lower()
    code = primary.split(";")[0].split("-")[0].strip()
    return EN if code == EN else DEFAULT


def _enabled():
    return GoogleTranslator is not None


def _key(lang, text):
    return f"{lang}::{text}"


def t(text, lang=None):
    """Traduce un texto fijo al idioma activo (o al indicado).

    En español devuelve el texto tal cual. Nunca levanta excepciones: si
    algo falla, devuelve el texto original.
    """
    text = str(text) if text is not None else ""
    if not text.strip():
        return text
    lang = lang or getattr(g, "lang", DEFAULT)
    if lang == DEFAULT or not _enabled():
        return text
    mapping = translate_mapping([text], lang)
    return mapping.get(text, text)


def translate_mapping(texts, lang):
    """Traduce una lista de textos y devuelve {original: traducido}.

    Primero consulta la caché y traduce por lotes únicamente lo que falte,
    de modo que la renderización no haga una petición por texto.
    """
    texts = list(dict.fromkeys(texts))
    mapping = {}
    missing = []
    with _cache_lock:
        for src in texts:
            key = _key(lang, src)
            if key in _cache:
                mapping[src] = _cache[key]
            else:
                missing.append(src)
    if missing and _enabled():
        translated = _batch(missing, lang)
        with _cache_lock:
            for src, tr in zip(missing, translated):
                _cache[_key(lang, src)] = tr
                mapping[src] = tr
        _save_cache()
    for src in missing:
        mapping.setdefault(src, src)
    return mapping


def _batch(texts, lang):
    try:
        translator = GoogleTranslator(source=ES, target=lang)
        return translator.translate_batch(texts, sleep_seconds=0.1)
    except Exception:
        return [_single(text, lang) for text in texts]


def _single(text, lang):
    try:
        return GoogleTranslator(source=ES, target=lang).translate(text)
    except Exception:
        return text


class Localized:
    """Proxy sobre un objeto de BD que muestra traducidos ciertos atributos.

    Los campos se resuelven contra un mapa de traducciones ya cacheadas,
    así que renderizar no dispara llamadas de red.
    """

    def __init__(self, obj, fields, mapping):
        self._obj = obj
        self._fields = fields
        self._mapping = mapping

    def __getattr__(self, name):
        value = getattr(self._obj, name)
        if name in self._fields and isinstance(value, str) and value:
            return self._mapping.get(value, value)
        return value

    def __repr__(self):
        return f"<Localized {self._obj!r}>"


def localize(obj, fields):
    """Envuelve un objeto para que sus campos de texto se muestren traducidos."""
    lang = getattr(g, "lang", DEFAULT)
    if lang == DEFAULT or not obj:
        return obj
    texts = [getattr(obj, f) for f in fields
             if getattr(obj, f, None) and isinstance(getattr(obj, f), str)]
    mapping = translate_mapping(texts, lang)
    return Localized(obj, fields, mapping)


def localize_block(block):
    return localize(block, BLOCK_FIELDS.get(block.section_key, []))


def localize_service(service):
    return localize(service, list(SERVICE_FIELDS))


def localize_review(review):
    return localize(review, list(REVIEW_FIELDS))


def _prewarm(app):
    """Traduce por lotes, en segundo plano, el contenido actual + textos fijos."""
    try:
        with app.app_context():
            from models import ContentBlock, Review, Service

            texts = list(_STATIC_STRINGS)
            for block in ContentBlock.query.all():
                for field in BLOCK_FIELDS.get(block.section_key, []):
                    value = getattr(block, field, None)
                    if value and isinstance(value, str):
                        texts.append(value)
            for service in Service.query.all():
                for field in SERVICE_FIELDS:
                    value = getattr(service, field, None)
                    if value and isinstance(value, str):
                        texts.append(value)
            for review in Review.query.all():
                if review.comment:
                    texts.append(review.comment)
            translate_mapping(list(dict.fromkeys(texts)), EN)
    except Exception:
        # La precarga es opcional; si falla, la traducción se hace bajo demanda.
        pass
