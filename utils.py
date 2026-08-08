import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]
    )


def save_upload(file_storage, subfolder):
    """Save an uploaded file to static/uploads/<subfolder> with a unique name.
    Returns the relative path (from /static/) to store in the DB, or None."""
    if not file_storage or file_storage.filename == "":
        return None
    if not allowed_file(file_storage.filename):
        return None

    ext = file_storage.filename.rsplit(".", 1)[1].lower()
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
