# -*- coding: utf-8 -*-
"""
VetMind AI Enterprise - Media & File Storage Service (media_storage.py)
"""

import os
import io
import uuid
import base64
import hashlib
import time
import urllib.request
import urllib.parse
import urllib.error
import json
from datetime import datetime
from PIL import Image, ImageOps

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
if os.environ.get("VERCEL") or not os.access(BASE_DIR, os.W_OK):
    UPLOAD_DIR = "/tmp/uploads"

try:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
except Exception:
    pass

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".jfif", ".png", ".webp", ".gif", ".bmp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov"}
ALLOWED_DOC_EXTENSIONS = {".pdf"}

MAX_IMAGE_BYTES = 5 * 1024 * 1024   # 5 MB max per image
MAX_VIDEO_BYTES = 15 * 1024 * 1024  # 15 MB max per video
MAX_DOC_BYTES = 8 * 1024 * 1024     # 8 MB max per document


class MediaValidationError(ValueError):
    pass


def validate_and_process_upload(
    raw_bytes: bytes,
    filename: str,
    content_type: str = "",
    allow_video: bool = True,
    allow_doc: bool = False,
    max_image_dim: int = 1200,
    jpeg_quality: int = 82
) -> dict:
    if not raw_bytes or len(raw_bytes) < 16:
        raise MediaValidationError("الملف المرفوع فارغ أو تالف.")

    clean_name = os.path.basename(filename or "upload.bin")
    ext = os.path.splitext(clean_name)[1].lower()
    ctype = (content_type or "").lower().strip()

    is_img = (ext in ALLOWED_IMAGE_EXTENSIONS) or ctype.startswith("image/")
    is_vid = allow_video and ((ext in ALLOWED_VIDEO_EXTENSIONS) or ctype.startswith("video/"))
    is_doc = allow_doc and ((ext in ALLOWED_DOC_EXTENSIONS) or ctype == "application/pdf")

    if not (is_img or is_vid or is_doc):
        raise MediaValidationError(
            f"صيغة الملف ({ext or ctype}) غير مدعومة. الصيغ المسموحة: صور (JPG, PNG, WEBP, GIF)"
            + (" أو فيديو (MP4, WEBM)" if allow_video else "")
        )

    if is_img:
        if len(raw_bytes) > MAX_IMAGE_BYTES:
            size_mb = round(len(raw_bytes) / (1024 * 1024), 2)
            raise MediaValidationError(
                f"حجم الصورة ({size_mb} ميجابايت) يتجاوز الحد الأقصى المسموح به (5 ميجابايت)."
            )
        try:
            im = Image.open(io.BytesIO(raw_bytes))
            im.verify()
            im = Image.open(io.BytesIO(raw_bytes))
            im = ImageOps.exif_transpose(im)
        except Exception as e:
            raise MediaValidationError("الملف المرفوع ليس صورة صالحة أو أنه تالف ولا يمكن قراءته.") from e

        out_buf = io.BytesIO()
        if im.format == "GIF" and getattr(im, "is_animated", False):
            processed_bytes = raw_bytes
            final_mime = "image/gif"
            final_ext = ".gif"
        else:
            if im.mode in ("RGBA", "LA", "P"):
                bg = Image.new("RGB", im.size, (255, 255, 255))
                if im.mode == "P":
                    im = im.convert("RGBA")
                bg.paste(im, mask=im.split()[-1] if im.mode in ("RGBA", "LA") else None)
                im = bg
            elif im.mode != "RGB":
                im = im.convert("RGB")

            if max(im.size) > max_image_dim:
                im.thumbnail((max_image_dim, max_image_dim), Image.Resampling.LANCZOS)

            im.save(out_buf, format="JPEG", quality=jpeg_quality, optimize=True)
            processed_bytes = out_buf.getvalue()
            final_mime = "image/jpeg"
            final_ext = ".jpg"

        unique_fname = f"img_{int(time.time())}_{uuid.uuid4().hex[:8]}{final_ext}"
        b64_str = base64.b64encode(processed_bytes).decode("ascii")
        return {
            "filename": unique_fname,
            "media_type": "image",
            "mime_type": final_mime,
            "processed_bytes": processed_bytes,
            "data_b64": b64_str,
            "data_uri": f"data:{final_mime};base64,{b64_str}",
            "size_bytes": len(processed_bytes)
        }

    elif is_vid:
        if len(raw_bytes) > MAX_VIDEO_BYTES:
            size_mb = round(len(raw_bytes) / (1024 * 1024), 2)
            raise MediaValidationError(
                f"حجم الفيديو ({size_mb} ميجابايت) يتجاوز الحد الأقصى المسموح به (15 ميجابايت)."
            )
        final_ext = ext if ext in ALLOWED_VIDEO_EXTENSIONS else ".mp4"
        final_mime = "video/webm" if final_ext == ".webm" else ("video/quicktime" if final_ext == ".mov" else "video/mp4")
        unique_fname = f"vid_{int(time.time())}_{uuid.uuid4().hex[:8]}{final_ext}"
        b64_str = base64.b64encode(raw_bytes).decode("ascii")
        return {
            "filename": unique_fname,
            "media_type": "video",
            "mime_type": final_mime,
            "processed_bytes": raw_bytes,
            "data_b64": b64_str,
            "data_uri": f"data:{final_mime};base64,{b64_str}",
            "size_bytes": len(raw_bytes)
        }

    else:
        if len(raw_bytes) > MAX_DOC_BYTES:
            raise MediaValidationError("حجم المستند يتجاوز الحد المسموح به (8 ميجابايت).")
        if not raw_bytes.startswith(b"%PDF"):
            raise MediaValidationError("المستند المرفوع ليس ملف PDF صالحاً.")
        unique_fname = f"doc_{int(time.time())}_{uuid.uuid4().hex[:8]}.pdf"
        b64_str = base64.b64encode(raw_bytes).decode("ascii")
        return {
            "filename": unique_fname,
            "media_type": "document",
            "mime_type": "application/pdf",
            "processed_bytes": raw_bytes,
            "data_b64": b64_str,
            "data_uri": f"data:application/pdf;base64,{b64_str}",
            "size_bytes": len(raw_bytes)
        }


def _upload_to_cloudinary(processed_bytes: bytes, filename: str, media_type: str) -> str | None:
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME", "").strip()
    api_key = os.environ.get("CLOUDINARY_API_KEY", "").strip()
    api_secret = os.environ.get("CLOUDINARY_API_SECRET", "").strip()

    if not (cloud_name and api_key and api_secret):
        return None
    if cloud_name.startswith("your_") or api_key.startswith("your_"):
        return None

    try:
        timestamp = str(int(time.time()))
        folder = "vetmind_media"
        to_sign = f"folder={folder}&timestamp={timestamp}{api_secret}"
        signature = hashlib.sha1(to_sign.encode("utf-8")).hexdigest()

        res_type = "video" if media_type == "video" else "image"
        url = f"https://api.cloudinary.com/v1_1/{cloud_name}/{res_type}/upload"

        boundary = f"----VetMindBoundary{uuid.uuid4().hex}"
        body_parts = []

        def add_field(name, val):
            body_parts.append(f"--{boundary}\r\n".encode("utf-8"))
            body_parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n{val}\r\n'.encode("utf-8"))

        add_field("api_key", api_key)
        add_field("timestamp", timestamp)
        add_field("folder", folder)
        add_field("signature", signature)

        body_parts.append(f"--{boundary}\r\n".encode("utf-8"))
        body_parts.append(
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n".encode("utf-8")
        )
        body_parts.append(processed_bytes)
        body_parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))

        payload = b"".join(body_parts)
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            return resp_data.get("secure_url")
    except Exception as e:
        print("Cloudinary upload fallback notice:", e)
        return None


def store_media_permanently(
    conn,
    raw_bytes: bytes,
    original_filename: str,
    content_type: str = "",
    owner_id: int = 0,
    is_private: int = 0,
    allow_video: bool = True,
    prefer_data_uri: bool = False
) -> dict:
    info = validate_and_process_upload(
        raw_bytes=raw_bytes,
        filename=original_filename,
        content_type=content_type,
        allow_video=allow_video
    )
    fname = info["filename"]

    for d in [UPLOAD_DIR, os.path.join(BASE_DIR, "uploads")]:
        try:
            os.makedirs(d, exist_ok=True)
            if os.access(d, os.W_OK):
                with open(os.path.join(d, fname), "wb") as f:
                    f.write(info["processed_bytes"])
        except Exception:
            pass

    if not is_private:
        cloud_url = _upload_to_cloudinary(info["processed_bytes"], fname, info["media_type"])
        if cloud_url:
            return {
                "filename": fname,
                "url": cloud_url,
                "media_type": info["media_type"],
                "mime_type": info["mime_type"],
                "size_bytes": info["size_bytes"]
            }

    if conn is not None:
        try:
            c = conn.cursor()
            c.execute(
                """
                INSERT OR REPLACE INTO media_files (filename, mime_type, data_b64, size_bytes, owner_id, is_private, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fname,
                    info["mime_type"],
                    info["data_b64"],
                    info["size_bytes"],
                    int(owner_id or 0),
                    int(is_private or 0),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
            )
            conn.commit()
        except Exception as e:
            print("Database media_files insert notice:", e)

    if prefer_data_uri and info["size_bytes"] <= 1.2 * 1024 * 1024:
        url = info["data_uri"]
    else:
        url = f"/uploads/{fname}"

    return {
        "filename": fname,
        "url": url,
        "media_type": info["media_type"],
        "mime_type": info["mime_type"],
        "size_bytes": info["size_bytes"]
    }


def get_media_from_db(conn, filename: str) -> dict | None:
    if not filename or conn is None:
        return None
    clean_name = os.path.basename(filename)
    try:
        c = conn.cursor()
        c.execute(
            "SELECT mime_type, data_b64, owner_id, is_private FROM media_files WHERE filename = ?",
            (clean_name,)
        )
        row = c.fetchone()
        if not row:
            return None
        raw = base64.b64decode(row["data_b64"])
        return {
            "mime_type": row["mime_type"],
            "bytes": raw,
            "owner_id": row["owner_id"],
            "is_private": row["is_private"]
        }
    except Exception:
        return None


def delete_media_permanently(conn, filename: str) -> bool:
    """
    Permanently deletes a media file from:
    1. Local uploads directory and temporary directories
    2. Database media_files table
    Ensuring zero residue on disk or database.
    """
    if not filename:
        return False
    clean_name = os.path.basename(filename.strip())
    if not clean_name:
        return False

    # 1. Physical disk & temp removal
    for d in [UPLOAD_DIR, os.path.join(BASE_DIR, "uploads"), "/tmp/uploads"]:
        try:
            fpath = os.path.join(d, clean_name)
            if os.path.exists(fpath) and os.path.isfile(fpath):
                os.remove(fpath)
        except Exception:
            pass

    # 2. Database permanent record removal
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute("DELETE FROM media_files WHERE filename = ?", (clean_name,))
            conn.commit()
        except Exception:
            pass

    return True
