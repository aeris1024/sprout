"""Bounded, read-only image decoding for the desktop preview viewer."""
from __future__ import annotations

import base64
import io
import tempfile
import warnings
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from .errors import SproutError
from .repository import Repository

MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000
MAX_IMAGE_SIDE = 8192
DISPLAY_SIDE = 2048
FORMATS = {"PNG", "JPEG", "WEBP", "BMP"}


def render_preview_image(repository: Repository, commit: str, attachment_id: str) -> dict:
    """Decode only a selected preview, returning a static PNG without altering its source."""
    attachment = repository.preview(commit, attachment_id)
    if attachment.size > MAX_IMAGE_BYTES:
        raise SproutError("画像が表示上限の20 MiBを超えています。取り出して確認してください", code="preview_image_too_large")
    with tempfile.TemporaryDirectory(prefix="sprout-preview-image-") as directory:
        source = repository.export_preview(commit, attachment.id, Path(directory) / "source.bin")
        if source.stat().st_size > MAX_IMAGE_BYTES:
            raise SproutError("画像が表示上限の20 MiBを超えています。取り出して確認してください", code="preview_image_too_large")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(source) as image:
                    if image.format not in FORMATS:
                        raise SproutError("画像表示はPNG・JPEG・静止WebP・BMPに対応しています", code="unsupported_preview_image")
                    width, height = image.size
                    if width > MAX_IMAGE_SIDE or height > MAX_IMAGE_SIDE or width * height > MAX_IMAGE_PIXELS:
                        raise SproutError("画像の表示上限（一辺8192px・1600万画素）を超えています。取り出して確認してください", code="preview_image_too_large")
                    if getattr(image, "n_frames", 1) != 1:
                        raise SproutError("アニメーション画像の表示にはまだ対応していません", code="animated_preview_image")
                    image.load()
                    with ImageOps.exif_transpose(image) as oriented:
                        width, height = oriented.size
                        oriented.thumbnail((DISPLAY_SIDE, DISPLAY_SIDE), Image.Resampling.LANCZOS)
                        with oriented.convert("RGBA") as display:
                            output = io.BytesIO()
                            display.save(output, format="PNG")
                            return {
                                "data_url": "data:image/png;base64," + base64.b64encode(output.getvalue()).decode("ascii"),
                                "width": width, "height": height,
                                "display_width": display.width, "display_height": display.height,
                            }
        except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise SproutError("画像の画素数が表示上限を超えています", code="preview_image_too_large") from exc
        except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
            raise SproutError("画像が破損しているか、表示に対応していない形式です。取り出して確認してください", code="invalid_preview_image") from exc
