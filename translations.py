"""Automatic site translation with deep-translator.

Content is written in English. When the visitor chooses Spanish (or we
detect it automatically) we translate with deep-translator (Google) and
cache the result —in memory and in a JSON file— to avoid repeated network
calls and make subsequent visits instant.

Usage:
  - Fixed texts in templates:   {{ t('Text in English') }}
  - DB objects:                 localize(obj, fields)  -> proxy that translates
                                  the indicated attributes at render time
  - Active language:            g.lang  ('es' | 'en')
"""
import json
import logging
import os
import threading

from flask import current_app, g, request

try:
    from deep_translator import GoogleTranslator
except Exception:  # pragma: no cover — deep-translator no instalado
    GoogleTranslator = None

ES = "es"
EN = "en"
SUPPORTED = (ES, EN)
DEFAULT = EN

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
SERVICE_FIELDS = ("name", "short_description", "description", "work_methods")
REVIEW_FIELDS = ("comment",)
TRUST_CARD_FIELDS = ("title", "body")

# Fixed texts from public templates. Preloaded at startup so that
# the first Spanish-speaking visitor doesn't wait for translations.
_STATIC_STRINGS = [
    # Navigation
    "Home", "Reviews", "Quote", "Get your quote",
    "Request a quote", "Request a Quote", "Call Us Today",
    "Experts in residential and commercial roofing",
    "View products", "View details",
    "View all / leave a review", "Leave a review", "Back to home",
    "View reviews", "Admin access", "Services", "Contact", "Social media",
    "All rights reserved.", "Modules", "Open menu", "More", "More products", "Main menu",
    "Language", "Spanish", "English",
    # Home
    "Roofs, Facades and Prefabricated Modules",
    "Roofs, Facades and Prefabricated Modules in El Salvador",
    "Design, supply and installation of industrial roofs, metal facades "
    "and prefabricated modules in El Salvador.",
    "Building trust in every project",
    "Products", "Systems for every type of project",
    "Manufacturing, supply and installation with warranty for residential, "
    "commercial and industrial projects.",
    "Our commitment", "What sets us apart?",
    "Years of Standing Seam warranty", "Customer support",
    "Professional installation", "Construction systems",
    "Over 5 years of experience", "Years of experience", "Years of", "experience",
    "Professional quality seal in residential and commercial roofing",
    "Long-lasting protection with certified roof systems and real backing.",
    "Continuous support for emergencies, maintenance and project follow-up.",
    "Specialized crews, flawless finishes and safety in every project.",
    "Standing Seam, thermoacoustic panels and modules adapted to each project.",
    "Project gallery",
    "About us", "We Build Trust", "Our values",
    "Mission", "Vision", "24/7 Support", "Call:",
    "Services", "Contact", "Social media", "Follow us and contact us",
    "Leave a review", "All rights reserved.", "Admin access",
    "Tecuns Client", "stars",
    "No reviews published yet. Be the first to share your experience!",
    "Ready to build your next project?",
    "No obligation · Quick response · Custom projects",
    "Tell us the location, what you need and upload site photos. "
    "We'll send you a no-obligation quote.",
    # Reviews
    "Customer reviews", "Our customers' experience",
    "Completed projects, real opinions. Share yours too.",
    "Published reviews", "Featured reviews", "Leave your review",
    "Your review will be published after being reviewed by our team.",
    "Tell us how it went. Your review will be published after being reviewed by our team.",
    "Your opinion", "Community", "All reviews",
    "Name", "Email (optional)", "Rating", "Comment",
    "Tell us about your project and experience with Tecuns Roofing...",
    "Submit review",
    # Quote
    "Tell us about your project",
    "Give us the location, describe what you need and upload site photos. "
    "Our team will review your request and contact you with a proposal.",
    "Full name", "Phone / WhatsApp", "Product of interest",
    "Select an option", "Other / Not sure",
    "Project location",
    "Department, municipality, address or reference point",
    "Enter the address or use the map below to mark the exact "
    "point — it will autocomplete.",
    "Mark location on map (optional)",
    "Use my current location", "Search address, neighborhood or city...",
    "You haven't marked a point yet — the map is centered on El Salvador. "
    "Click to place the pin.",
    "Describe what you need",
    "Type of roof or facade, approximate dimensions, current condition, deadlines, etc.",
    "Site photos (optional, up to 6 images)",
    "Upload photos of the roof, facade or project area — helps us "
    "prepare a more accurate quote.",
    "Submit quote request",
    "Contact details", "How we'll contact you with your quote.",
    "Enter the address or mark the point on the map.",
    "Job details", "The clearer, the more accurate your quote.",
    "Drag or select photos", "Benefits",
    "No obligation", "Quick response", "Custom projects",
    # Service detail
    "Product", "Service", "Technical description", "About this system",
    "About this service", "Quote this product", "Quote this service",
    "Other products", "More services", "You may also like",
    "Explore other roofing solutions with the same Tecuns quality standard.",
    "View service", "Ready to quote this service?",
    "Gallery", "Projects of this service",
    "Real photos of projects completed by Tecun's Roofing.",
    "Continue viewing",
    "Work methods", "Work method", "Our work method",
    "How we carry out this service, step by step.",
    "Enlarge photo", "Close", "Previous", "Next",
    # Thanks
    "Request sent", "Request received",
    "Thank you! Your request was sent",
    "Our team will review your project information and photos, and "
    "contact you soon with your quote.",
    # Error 404 / 500
    "Error", "Page not found",
    "Sorry, the page you're looking for doesn't exist or was moved.",
    "Something went wrong",
    "An unexpected error occurred. Please try again in a few minutes.",
]

_cache = {}
_cache_lock = threading.Lock()
_MAX_CACHE = 6000
_cache_file = None  # defined in init_app()


def init_app(app):
    """Configure persistent cache and pre-warm translations in background."""
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
    """before_request: active language = user cookie > Accept-Language."""
    lang = request.cookies.get("lang")
    if lang not in SUPPORTED:
        lang = detect_lang()
    g.lang = lang


def detect_lang():
    """Detect language from browser's Accept-Language header.

    A visitor in the USA typically sends 'en-US...' (→ English); in LATAM
    'es-*' (→ Spanish). The manual selector always takes priority.
    """
    accept = request.headers.get("Accept-Language", "")
    primary = accept.split(",")[0].strip().lower()
    code = primary.split(";")[0].split("-")[0].strip()
    return ES if code == ES else EN


def _enabled():
    return GoogleTranslator is not None


def _key(lang, text):
    return f"{lang}::{text}"


def t(text, lang=None):
    """Translate a fixed text to the active language (or specified one).

    In English returns the text as-is. Never raises exceptions: if
    something fails, returns the original text.
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
        translator = GoogleTranslator(source=EN, target=lang)
        return translator.translate_batch(texts, sleep_seconds=0.1)
    except Exception as e:
        _log_translation_failure("batch", texts, lang, e)
        return [_single(text, lang) for text in texts]


def _single(text, lang):
    try:
        return GoogleTranslator(source=EN, target=lang).translate(text)
    except Exception as e:
        _log_translation_failure("single", text, lang, e)
        return text


def _log_translation_failure(mode, texts, lang, exc):
    """Log a translation failure with context for debugging."""
    msg = f"Translation failed ({mode} mode, target={lang}): {exc}"
    # Include the text(s) that failed (truncated to avoid huge logs)
    if isinstance(texts, list):
        truncated = [t[:100] + ("..." if len(t) > 100 else "") for t in texts]
        msg += f" | texts: {truncated}"
    else:
        truncated = texts[:100] + ("..." if len(texts) > 100 else "")
        msg += f" | text: {truncated}"
    # Prefer Flask's current_app.logger; fall back to stdlib logging
    try:
        current_app.logger.warning(msg)
    except RuntimeError:
        logging.warning(msg)


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


def localize_trust_card(card):
    return localize(card, list(TRUST_CARD_FIELDS))


def _prewarm(app):
    """Traduce por lotes, en segundo plano, el contenido actual + textos fijos."""
    try:
        with app.app_context():
            from models import ContentBlock, Review, Service, TrustCard

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
            for card in TrustCard.query.all():
                for field in TRUST_CARD_FIELDS:
                    value = getattr(card, field, None)
                    if value and isinstance(value, str):
                        texts.append(value)
            translate_mapping(list(dict.fromkeys(texts)), ES)
    except Exception:
        # La precarga es opcional; si falla, la traducción se hace bajo demanda.
        pass
