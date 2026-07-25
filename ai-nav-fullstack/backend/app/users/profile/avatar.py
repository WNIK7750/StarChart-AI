import os
import tempfile
import warnings
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from time import perf_counter

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import (
    AVATAR_MAX_DIMENSION,
    AVATAR_MAX_FRAMES,
    AVATAR_MAX_OUTPUT_BYTES,
    AVATAR_MAX_SOURCE_PIXELS,
    AVATAR_MAX_UPLOAD_BYTES,
    AVATAR_PROCESSING_TIMEOUT_SECONDS,
    UPLOAD_DIR,
)
from app.core.security import random_uid
from app.users.common import UsersError


ALLOWED_AVATAR_TYPES = {
    "JPEG": {"image/jpeg"},
    "PNG": {"image/png"},
    "WEBP": {"image/webp"},
    "GIF": {"image/gif"},
}


def _detect_image_format(content: bytes) -> str | None:
    if content.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return "GIF"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "WEBP"
    return None


@dataclass(frozen=True)
class ProcessedAvatar:
    data: bytes
    original_bytes: int
    original_width: int
    original_height: int
    width: int
    height: int


class AvatarProcessor:
    def __init__(
        self,
        max_upload_bytes: int = AVATAR_MAX_UPLOAD_BYTES,
        max_output_bytes: int = AVATAR_MAX_OUTPUT_BYTES,
        max_dimension: int = AVATAR_MAX_DIMENSION,
        max_source_pixels: int = AVATAR_MAX_SOURCE_PIXELS,
        max_frames: int = AVATAR_MAX_FRAMES,
        max_processing_seconds: float = AVATAR_PROCESSING_TIMEOUT_SECONDS,
    ):
        self.max_upload_bytes = max_upload_bytes
        self.max_output_bytes = max_output_bytes
        self.max_dimension = max_dimension
        self.max_source_pixels = max_source_pixels
        self.max_frames = max_frames
        self.max_processing_seconds = max_processing_seconds

    def process(self, content: bytes, content_type: str | None) -> ProcessedAvatar:
        started = perf_counter()

        def check_deadline() -> None:
            if perf_counter() - started > self.max_processing_seconds:
                raise UsersError("AVATAR_PROCESSING_TIMEOUT", "头像处理超过时间限制", 413)

        if not content:
            raise UsersError("AVATAR_EMPTY", "上传文件为空", 422)
        if len(content) > self.max_upload_bytes:
            raise UsersError("AVATAR_TOO_LARGE", "头像原图超过大小限制", 413)
        if content_type not in {mime for values in ALLOWED_AVATAR_TYPES.values() for mime in values}:
            raise UsersError("AVATAR_CONTENT_TYPE_UNSUPPORTED", "头像文件类型不受支持", 415)
        detected_format = _detect_image_format(content)
        if detected_format is None:
            raise UsersError("AVATAR_FORMAT_UNSUPPORTED", "头像文件签名不受支持", 415)
        if content_type not in ALLOWED_AVATAR_TYPES[detected_format]:
            raise UsersError("AVATAR_CONTENT_TYPE_MISMATCH", "头像文件类型与内容不一致", 415)
        check_deadline()

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(content)) as probe:
                    if probe.format != detected_format:
                        raise UsersError("AVATAR_FORMAT_UNSUPPORTED", "头像图片格式不受支持", 415)
                    probe.verify()
                check_deadline()
                image = Image.open(BytesIO(content))
                image_format = image.format
                original_width, original_height = image.size
                if original_width <= 0 or original_height <= 0:
                    raise UsersError("AVATAR_DIMENSIONS_INVALID", "头像尺寸无效", 422)
                if original_width * original_height > self.max_source_pixels:
                    raise UsersError("AVATAR_PIXEL_LIMIT_EXCEEDED", "头像像素尺寸超过限制", 413)
                if image_format not in ALLOWED_AVATAR_TYPES:
                    raise UsersError("AVATAR_FORMAT_UNSUPPORTED", "头像图片格式不受支持", 415)
                if content_type not in ALLOWED_AVATAR_TYPES[image_format]:
                    raise UsersError("AVATAR_CONTENT_TYPE_MISMATCH", "头像文件类型与图片内容不一致", 415)
                if getattr(image, "n_frames", 1) > self.max_frames:
                    raise UsersError("AVATAR_FRAME_LIMIT_EXCEEDED", "头像帧数超过限制", 413)
                image.load()
                check_deadline()
        except UsersError:
            raise
        except (Image.DecompressionBombError, Image.DecompressionBombWarning):
            raise UsersError("AVATAR_PIXEL_LIMIT_EXCEEDED", "头像像素尺寸超过限制", 413) from None
        except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
            raise UsersError("AVATAR_INVALID_IMAGE", "无法识别上传的图片", 422) from None

        image = ImageOps.exif_transpose(image)
        if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
            rgba = image.convert("RGBA")
            background = Image.new("RGBA", rgba.size, "white")
            image = Image.alpha_composite(background, rgba).convert("RGB")
        else:
            image = image.convert("RGB")
        image.thumbnail((self.max_dimension, self.max_dimension), Image.Resampling.LANCZOS)
        check_deadline()

        output = BytesIO()
        quality = 84
        while True:
            output.seek(0)
            output.truncate(0)
            image.save(output, format="WEBP", quality=quality, method=6)
            check_deadline()
            if output.tell() <= self.max_output_bytes or quality <= 58:
                break
            quality -= 8
        if output.tell() > self.max_output_bytes:
            raise UsersError("AVATAR_OUTPUT_TOO_LARGE", "头像压缩后仍然超过大小限制", 413)

        return ProcessedAvatar(
            data=output.getvalue(),
            original_bytes=len(content),
            original_width=original_width,
            original_height=original_height,
            width=image.width,
            height=image.height,
        )


class AvatarStorage:
    def __init__(self, upload_dir: Path = UPLOAD_DIR):
        self.avatar_dir = upload_dir / "avatars"

    def store(self, data: bytes) -> tuple[str, Path]:
        self.avatar_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{random_uid('avatar')}.webp"
        final_path = self.avatar_dir / filename
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(dir=self.avatar_dir, prefix=".avatar_", suffix=".tmp", delete=False) as handle:
                temporary_path = Path(handle.name)
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, final_path)
        except Exception:
            if temporary_path:
                temporary_path.unlink(missing_ok=True)
            final_path.unlink(missing_ok=True)
            raise
        return f"/uploads/avatars/{filename}", final_path

    @staticmethod
    def remove_path(path: Path) -> None:
        path.unlink(missing_ok=True)

    def remove_managed_url(self, avatar_url: str | None, exclude: Path | None = None) -> bool | None:
        if not avatar_url or not avatar_url.startswith("/uploads/avatars/"):
            return None
        filename = avatar_url.removeprefix("/uploads/avatars/")
        if not filename or Path(filename).name != filename or not filename.endswith(".webp"):
            return None
        candidate = self.avatar_dir / filename
        if exclude and candidate.resolve() == exclude.resolve():
            return None
        try:
            candidate.unlink(missing_ok=True)
            return True
        except OSError:
            return False
