import os
from datetime import timedelta

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _csv_env(name: str, default: str = "") -> list[str]:
    """Parsea una variable de entorno como lista CSV, limpiando vacíos."""
    val = os.environ.get(name, default)
    return [v.strip() for v in val.split(",") if v.strip()]


def _resolve_secret_key() -> str:
    """SECRET_KEY desde env, o archivo estable en instance/ (nunca un default público fijo)."""
    env_key = os.environ.get("SECRET_KEY", "").strip()
    if env_key:
        return env_key

    secret_path = os.path.join(BASE_DIR, "instance", "secret_key")
    try:
        if os.path.isfile(secret_path):
            with open(secret_path, encoding="utf-8") as fh:
                stored = fh.read().strip()
            if stored:
                return stored
        os.makedirs(os.path.dirname(secret_path), exist_ok=True)
        generated = os.urandom(32).hex()
        with open(secret_path, "w", encoding="utf-8") as fh:
            fh.write(generated)
        return generated
    except OSError:
        # Último recurso si instance/ no es escribible
        return os.urandom(32).hex()


class Config:
    SECRET_KEY = _resolve_secret_key()
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "instance", "tecuns.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Recargar plantillas HTML al guardar (evita menú/CSS “viejos” en desarrollo)
    TEMPLATES_AUTO_RELOAD = True
    SEND_FILE_MAX_AGE_DEFAULT = 0

    # Cookies de sesión endurecidas
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # En producción (HTTPS) define SESSION_COOKIE_SECURE=1
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "").lower() in (
        "1",
        "true",
        "yes",
    )
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    REMEMBER_COOKIE_DURATION = timedelta(days=7)

    # CSRF (Flask-WTF)
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 60 * 60 * 8  # 8 horas

    # Dominio público canónico para el sitemap.xml (sin barra final).
    # Si está vacío se usa el Host de la petición.
    SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")

    UPLOAD_FOLDER_CONTENT = os.path.join(BASE_DIR, "static", "uploads", "content")
    UPLOAD_FOLDER_QUOTES = os.path.join(BASE_DIR, "static", "uploads", "quotes")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
    ALLOWED_VIDEO_EXTENSIONS = {"mp4", "webm", "mov"}
    MAX_CONTENT_LENGTH = 64 * 1024 * 1024  # 64 MB (imágenes + videos de servicio)

    # =========================
    # Google reCAPTCHA
    # =========================
    # Claves: se obtienen en https://www.google.com/recaptcha/admin/create
    # v2 = Checkbox "No soy un robot"; v3 = Invisible (score-based)
    RECAPTCHA_SITE_KEY = os.environ.get("RECAPTCHA_SITE_KEY", "")
    RECAPTCHA_SECRET_KEY = os.environ.get("RECAPTCHA_SECRET_KEY", "")
    RECAPTCHA_VERSION = os.environ.get("RECAPTCHA_VERSION", "v2")  # "v2" o "v3"
    RECAPTCHA_MIN_SCORE = float(os.environ.get("RECAPTCHA_MIN_SCORE", "0.5"))  # solo v3

    # =========================
    # Filtro anti-spam (listas editables via variables de entorno)
    # =========================
    SPAM_KEYWORDS = _csv_env(
        "SPAM_KEYWORDS",
        "bitcoin,crypto,mining,click here,viagra,casino,loan,debt,credit,earn money,make money,work from home",
    )
    SPAM_BLOCKED_DOMAINS = _csv_env(
        "SPAM_BLOCKED_DOMAINS",
        "tempmail.com,10minutemail.com,guerrillamail.com,mailinator.com,trashmail.com,yopmail.com",
    )
    SPAM_URL_SHORTENERS = _csv_env(
        "SPAM_URL_SHORTENERS",
        "bit.ly,tinyurl.com,goo.gl,ow.ly,is.gd,buff.ly,adf.ly,shorte.st",
    )
