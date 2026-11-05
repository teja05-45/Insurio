"""Secure local storage for uploaded PDFs.

Files are named by server-generated UUIDs. User-supplied filenames are only kept
as display metadata, so path traversal is structurally impossible.
"""

import hashlib
import re
import uuid
from pathlib import Path

from app.core.config import get_settings
from app.core.errors import AppError

CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")


def sanitize_filename(name: str) -> str:
    base = Path(name.replace("\\", "/")).name
    base = CONTROL_CHARS_RE.sub("", base).strip() or "policy.pdf"
    return base[:200]


def upload_root() -> Path:
    return Path(get_settings().UPLOAD_DIR).resolve()


def save_pdf(user_id: uuid.UUID, data: bytes) -> tuple[str, str]:
    """Persist bytes and return (storage_key, sha256)."""
    digest = hashlib.sha256(data).hexdigest()
    directory = upload_root() / str(user_id)
    directory.mkdir(parents=True, exist_ok=True)
    storage_key = f"{user_id}/{uuid.uuid4().hex}.pdf"
    path = (upload_root() / storage_key).resolve()
    if not path.is_relative_to(upload_root()):
        raise AppError("Invalid storage path.", code="invalid_storage", status_code=400)
    path.write_bytes(data)
    return storage_key, digest


def read_pdf(storage_key: str) -> bytes:
    path = (upload_root() / storage_key).resolve()
    if not path.is_relative_to(upload_root()) or not path.is_file():
        raise AppError("The document file is missing.", code="file_missing", status_code=404)
    return path.read_bytes()


def pdf_path(storage_key: str) -> Path:
    path = (upload_root() / storage_key).resolve()
    if not path.is_relative_to(upload_root()) or not path.is_file():
        raise AppError("The document file is missing.", code="file_missing", status_code=404)
    return path


def delete_pdf(storage_key: str) -> None:
    path = (upload_root() / storage_key).resolve()
    if path.is_relative_to(upload_root()) and path.is_file():
        path.unlink(missing_ok=True)
