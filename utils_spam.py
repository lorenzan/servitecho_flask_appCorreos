"""Utilidades anti-spam para formularios públicos.

Incluye:
- verify_recaptcha(token): valida token reCAPTCHA v2/v3 contra la API de Google.
- is_spam(nombre, comentario, email): detecta patrones de spam en el contenido.
"""
import re
import requests
from flask import current_app


# Expresión regular para detectar URLs
_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)

# Rangos Unicode de emojis comunes (básico)
_EMOJI_RE = re.compile(
    r"[\U0001F600-\U0001F64F"  # Emoticons
    r"\U0001F300-\U0001F5FF"  # Misc Symbols & Pictographs
    r"\U0001F680-\U0001F6FF"  # Transport & Map
    r"\U0001F1E0-\U0001F1FF"  # Flags
    r"\U00002700-\U000027BF"  # Dingbats
    r"\U0001F900-\U0001F9FF"  # Supplemental Symbols
    r"]"
)


def verify_recaptcha(token: str) -> tuple[bool, str]:
    """Valida un token reCAPTCHA (v2 o v3) con la API de Google.

    Args:
        token: El token recibido del frontend (g-recaptcha-response para v2,
               o token generado por grecaptcha.execute() para v3).

    Returns:
        Tupla (ok: bool, mensaje_error: str). Si ok=True, mensaje_error="".
    """
    secret = current_app.config.get("RECAPTCHA_SECRET_KEY")
    if not secret:
        return False, "reCAPTCHA is not configured on the server (missing RECAPTCHA_SECRET_KEY)."

    if not token or not token.strip():
        return False, "Empty reCAPTCHA token."

    try:
        resp = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={"secret": secret, "response": token.strip()},
            timeout=10,
        )
        data = resp.json()

        if not data.get("success"):
            # Códigos de error comunes: missing-input-secret, invalid-input-secret,
            # missing-input-response, invalid-input-response, bad-request, timeout-or-duplicate
            error_codes = data.get("error-codes", [])
            return False, f"reCAPTCHA validation failed: {', '.join(error_codes) or 'unknown'}."

        version = current_app.config.get("RECAPTCHA_VERSION", "v2")
        if version == "v3":
            score = data.get("score", 0.0)
            min_score = current_app.config.get("RECAPTCHA_MIN_SCORE", 0.5)
            if score < min_score:
                return False, f"Low reCAPTCHA score ({score:.2f} < {min_score}). Please try again."

        return True, ""

    except requests.Timeout:
        return False, "Timed out validating reCAPTCHA. Please try again."
    except requests.RequestException as e:
        return False, f"Network error validating reCAPTCHA: {e}"
    except Exception as e:
        current_app.logger.exception("Error inesperado en verify_recaptcha")
        return False, f"Error validating reCAPTCHA: {e}"


def is_spam(nombre: str, comentario: str, email: str) -> tuple[bool, str]:
    """Detecta patrones de spam en los datos del formulario de reseñas.

    Reglas comprobadas (en orden):
    1. Nombre y comentario idénticos (copia/pega automático).
    2. Nombre con excesivos caracteres especiales o emojis (no parece nombre real).
    3. Palabras clave de spam en el comentario (lista configurable).
    4. URLs con acortadores conocidos en el comentario (lista configurable).
    5. Dominio del email en lista negra de temporales/spam (lista configurable).

    Args:
        nombre: Campo "name" del formulario.
        comentario: Campo "comment" del formulario.
        email: Campo "email" del formulario (puede ser vacío).

    Returns:
        Tupla (es_spam: bool, razon: str). Si es_spam=False, razon="".
    """
    nombre = (nombre or "").strip()
    comentario = (comentario or "").strip()
    email = (email or "").strip().lower()

    # 1. Nombre == Comentario (repetido exacto, case-insensitive)
    if nombre and comentario and nombre.lower() == comentario.lower():
        return True, "Name and comment are identical."

    # 2. Nombre con muchos caracteres especiales / emojis
    if nombre:
        # Ratio de caracteres no alfanuméricos (permitimos acentos, espacios, guiones, puntos)
        special_chars = len(re.findall(r"[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s\-\.]", nombre))
        total_chars = max(len(nombre), 1)
        special_ratio = special_chars / total_chars

        has_emoji = bool(_EMOJI_RE.search(nombre))

        if special_ratio > 0.3 or has_emoji:
            return True, "The name contains unusual characters for a real name."

    # 3. Keywords de spam en comentario
    keywords = current_app.config.get("SPAM_KEYWORDS", [])
    comentario_lower = comentario.lower()
    for kw in keywords:
        kw_clean = kw.strip().lower()
        if kw_clean and kw_clean in comentario_lower:
            return True, f"Comment contains a blocked word: {kw_clean}"

    # 4. URLs con acortadores sospechosos en comentario
    urls = _URL_RE.findall(comentario)
    shorteners = current_app.config.get("SPAM_URL_SHORTENERS", [])
    for url in urls:
        url_lower = url.lower()
        for short in shorteners:
            short_clean = short.strip().lower()
            if short_clean and short_clean in url_lower:
                return True, f"URL shortener detected: {short_clean}"

    # 5. Dominio de email en lista negra
    if email and "@" in email:
        domain = email.split("@")[-1].lower()
        blocked_domains = [
            d.strip().lower() for d in current_app.config.get("SPAM_BLOCKED_DOMAINS", []) if d.strip()
        ]
        if domain in blocked_domains:
            return True, f"Blocked email domain: {domain}"

    return False, ""