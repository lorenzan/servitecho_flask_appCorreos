"""Re-optimize images already on disk (local or server).

Uses the same rules as new uploads:
  - max width 1600px
  - JPEG/WebP quality ~82
  - keeps the same filename/extension so DB paths stay valid

Usage (from project root, with venv active if you use one):

  # Preview only (no writes)
  python optimize_existing_images.py --dry-run

  # Optimize and overwrite files in place
  python optimize_existing_images.py

  # Only content/ or only quotes/
  python optimize_existing_images.py --folder content
  python optimize_existing_images.py --folder quotes

On PythonAnywhere: open a Bash console, cd to the project, activate the
virtualenv, run the same command, then reload the web app if needed.
"""
from __future__ import annotations

import argparse
import os
import sys
from io import BytesIO
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Pillow is required: pip install Pillow")
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent
UPLOADS_ROOT = BASE_DIR / "static" / "uploads"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_WIDTH = 1600
JPEG_QUALITY = 82
WEBP_QUALITY = 82


def optimize_file(path: Path, dry_run: bool = False) -> tuple[bool, str, int, int]:
    """Returns (changed, message, old_bytes, new_bytes)."""
    old_size = path.stat().st_size
    ext = path.suffix.lower().lstrip(".")

    try:
        with Image.open(path) as img:
            img.load()
            has_transparency = img.mode in ("RGBA", "LA") or (
                img.mode == "P" and "transparency" in img.info
            )
            original_width = img.width
            resized = False

            if img.width > MAX_WIDTH:
                ratio = MAX_WIDTH / img.width
                new_size = (MAX_WIDTH, int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                resized = True

            out = BytesIO()
            # Keep the same container format so paths in the DB stay valid
            if ext in ("jpg", "jpeg"):
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            elif ext == "webp":
                img.save(
                    out,
                    format="WEBP",
                    quality=WEBP_QUALITY,
                    method=6,
                    lossless=False,
                )
            elif ext == "png":
                # Keep PNG (logos / transparency). Don't convert to WebP so DB paths stay valid.
                if img.mode == "P" and not has_transparency:
                    img = img.convert("RGB")
                img.save(out, format="PNG", optimize=True)
            elif ext == "gif":
                if getattr(img, "is_animated", False):
                    return False, "skipped animated gif", old_size, old_size
                img.save(out, format="GIF", optimize=True)
            else:
                return False, f"unsupported .{ext}", old_size, old_size

            data = out.getvalue()
            new_size = len(data)

            if new_size >= old_size and not resized:
                return False, "already optimal", old_size, old_size

            if not dry_run:
                tmp = path.with_suffix(path.suffix + ".tmp")
                tmp.write_bytes(data)
                tmp.replace(path)

            saved_kb = (old_size - new_size) / 1024
            note = f"saved {saved_kb:.1f} KB"
            if resized:
                note += f", resized from {original_width}px wide"
            return True, note, old_size, new_size

    except Exception as e:
        return False, f"error: {e}", old_size, old_size


def main():
    parser = argparse.ArgumentParser(description="Optimize existing uploaded images in place.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report savings without writing files",
    )
    parser.add_argument(
        "--folder",
        choices=("content", "quotes", "all"),
        default="all",
        help="Which uploads subfolder to process",
    )
    parser.add_argument(
        "--min-kb",
        type=float,
        default=0,
        help="Only process files larger than this many KB (default: 0)",
    )
    args = parser.parse_args()

    if not UPLOADS_ROOT.is_dir():
        print(f"No uploads folder at {UPLOADS_ROOT}")
        sys.exit(1)

    roots = []
    if args.folder in ("content", "all"):
        roots.append(UPLOADS_ROOT / "content")
    if args.folder in ("quotes", "all"):
        roots.append(UPLOADS_ROOT / "quotes")

    files: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
                if p.stat().st_size >= args.min_kb * 1024:
                    files.append(p)

    if not files:
        print("No images found.")
        return

    print(f"Found {len(files)} image(s) under {UPLOADS_ROOT}")
    if args.dry_run:
        print("DRY RUN - no files will be modified\n")

    changed = 0
    skipped = 0
    errors = 0
    total_old = 0
    total_new = 0

    for path in sorted(files):
        ok, msg, old_b, new_b = optimize_file(path, dry_run=args.dry_run)
        rel = path.relative_to(UPLOADS_ROOT)
        total_old += old_b
        total_new += new_b if ok else old_b
        if ok:
            changed += 1
            print(f"  OK  {rel}  {old_b/1024:.1f}->{new_b/1024:.1f} KB  ({msg})")
        elif msg.startswith("error"):
            errors += 1
            print(f"  ERR {rel}  {msg}")
        else:
            skipped += 1
            print(f"  --  {rel}  {msg} ({old_b/1024:.1f} KB)")

    print("\n--- Summary ---")
    print(f"Changed: {changed}  Skipped: {skipped}  Errors: {errors}")
    print(f"Before: {total_old/1024/1024:.2f} MB")
    print(f"After:  {total_new/1024/1024:.2f} MB")
    print(f"Saved:  {(total_old-total_new)/1024/1024:.2f} MB")
    if args.dry_run:
        print("\nRe-run without --dry-run to apply changes.")


if __name__ == "__main__":
    main()
