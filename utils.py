import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app


def _ext(filename):
    if not filename or "." not in filename:
        return None
    return filename.rsplit(".", 1)[1].lower()


def allowed_file(filename):
    ext = _ext(filename)
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


def allowed_video(filename):
    ext = _ext(filename)
    return ext in current_app.config.get("ALLOWED_VIDEO_EXTENSIONS", set())


def save_upload(file_storage, subfolder, media="image"):
    """Save an uploaded file to static/uploads/<subfolder> with a unique name.

    media: "image" (default) or "video"
    Returns the relative path (from /static/) to store in the DB, or None.
    """
    if not file_storage or file_storage.filename == "":
        return None

    if media == "video":
        if not allowed_video(file_storage.filename):
            return None
    elif not allowed_file(file_storage.filename):
        return None

    ext = _ext(file_storage.filename)
    filename = f"{uuid.uuid4().hex}.{ext}"

    if subfolder == "content":
        folder = current_app.config["UPLOAD_FOLDER_CONTENT"]
        rel = f"uploads/content/{filename}"
    else:
        folder = current_app.config["UPLOAD_FOLDER_QUOTES"]
        rel = f"uploads/quotes/{filename}"

    os.makedirs(folder, exist_ok=True)
    file_storage.save(os.path.join(folder, filename))
    return rel
