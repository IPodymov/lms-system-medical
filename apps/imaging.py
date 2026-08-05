"""Shared processing for user-uploaded images (course covers, avatars, question images)."""

from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image

_QUALITY_AWARE_FORMATS = {"JPEG", "WEBP"}


def resize_uploaded_image(uploaded_file, *, max_dimension: int, quality: int = 85):
    """Return a new file with the image downscaled so neither side exceeds max_dimension.

    Preserves aspect ratio (only ever scales down, never crops), which keeps
    percentage-based coordinates — such as the click markers on quiz question
    images — valid regardless of the stored resolution.

    Returns the original file unchanged (rewound to the start) if it's empty,
    already within bounds, or not decodable as an image: upstream form/field
    validation is responsible for rejecting invalid uploads, so this never
    raises on bad input.
    """
    if not uploaded_file:
        return uploaded_file
    uploaded_file.seek(0)
    try:
        image = Image.open(uploaded_file)
        image.load()
    except OSError:
        uploaded_file.seek(0)
        return uploaded_file
    if image.width <= max_dimension and image.height <= max_dimension:
        uploaded_file.seek(0)
        return uploaded_file

    image_format = (image.format or "JPEG").upper()
    if image_format == "JPEG" and image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

    save_kwargs = {"optimize": True}
    if image_format in _QUALITY_AWARE_FORMATS:
        save_kwargs["quality"] = quality
    buffer = BytesIO()
    image.save(buffer, format=image_format, **save_kwargs)
    return ContentFile(buffer.getvalue(), name=uploaded_file.name)
