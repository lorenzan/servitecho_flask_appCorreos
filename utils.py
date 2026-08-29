import os
import uuid
from io import BytesIO
from werkzeug.utils import secure_filename
from flask import current_app

try:
    from PIL import Image
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False


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


def _optimize_image(file_storage, original_ext):
    """
    Optimize uploaded image using Pillow.
    - Resize if width > 1600px (maintain aspect ratio)
    - Save as JPEG quality 82, or WebP if original was WebP/PNG with transparency
    - Preserve transparency when present
    Returns (optimized_bytes, new_ext) or (None, None) on failure.
    """
    if not PIL_AVAILABLE:
        return None, None

    try:
        # Read file into memory
        file_storage.stream.seek(0)
        img_data = file_storage.stream.read()
        file_storage.stream.seek(0)

        img = Image.open(BytesIO(img_data))

        # Convert to RGB/RGBA as needed
        has_transparency = img.mode in ("RGBA", "LA") or (
            img.mode == "P" and "transparency" in img.info
        )

        # Resize if too wide
        max_width = 1600
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

        # Determine output format
        orig_ext = (original_ext or "").lower()
        if has_transparency or orig_ext in ("png", "webp"):
            # Use WebP for transparency
            output_ext = "webp"
            save_kwargs = {
                "format": "WEBP",
                "quality": 82,
                "method": 6,
                "lossless": False,
            }
        else:
            # Use JPEG for photos without transparency
            output_ext = "jpg"
            # Convert to RGB if needed (e.g., from RGBA without actual transparency)
            if img.mode in ("RGBA", "LA", "P"):
                # Check if there's actual transparency
                if has_transparency:
                    output_ext = "webp"
                    save_kwargs = {
                        "format": "WEBP",
                        "quality": 82,
                        "method": 6,
                        "lossless": False,
                    }
                else:
                    img = img.convert("RGB")
                    save_kwargs = {"format": "JPEG", "quality": 82, "optimize": True}
            else:
                save_kwargs = {"format": "JPEG", "quality": 82, "optimize": True}

        output = BytesIO()
        img.save(output, **save_kwargs)
        output.seek(0)
        return output.getvalue(), output_ext

    except Exception:
        # Any failure: return None to trigger fallback
        return None, None


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

    original_ext = _ext(file_storage.filename)
    filename = f"{uuid.uuid4().hex}"

    if subfolder == "content":
        folder = current_app.config["UPLOAD_FOLDER_CONTENT"]
        rel_prefix = "uploads/content/"
    else:
        folder = current_app.config["UPLOAD_FOLDER_QUOTES"]
        rel_prefix = "uploads/quotes/"

    os.makedirs(folder, exist_ok=True)

    # Try to optimize if it's an image and PIL is available
    if media == "image" and PIL_AVAILABLE:
        optimized_bytes, new_ext = _optimize_image(file_storage, original_ext)
        if optimized_bytes is not None and new_ext is not None:
            filename = f"{filename}.{new_ext}"
            filepath = os.path.join(folder, filename)
            with open(filepath, "wb") as f:
                f.write(optimized_bytes)
            return f"{rel_prefix}{filename}"

    # Fallback: save original file unchanged
    filename = f"{filename}.{original_ext}"
    filepath = os.path.join(folder, filename)
    file_storage.save(filepath)
    return f"{rel_prefix}{filename}"
