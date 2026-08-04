import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "instance", "servitecho.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER_CONTENT = os.path.join(BASE_DIR, "static", "uploads", "content")
    UPLOAD_FOLDER_QUOTES = os.path.join(BASE_DIR, "static", "uploads", "quotes")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB total per request
