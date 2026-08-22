import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "instance", "tecuns.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Dominio público canónico para el sitemap.xml (sin barra final).
    # Si está vacío se usa el Host de la petición.
    SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")

    UPLOAD_FOLDER_CONTENT = os.path.join(BASE_DIR, "static", "uploads", "content")
    UPLOAD_FOLDER_QUOTES = os.path.join(BASE_DIR, "static", "uploads", "quotes")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
    ALLOWED_VIDEO_EXTENSIONS = {"mp4", "webm", "mov"}
    MAX_CONTENT_LENGTH = 64 * 1024 * 1024  # 64 MB (imágenes + videos de servicio)
