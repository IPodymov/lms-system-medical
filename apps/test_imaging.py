from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image

from apps.imaging import resize_uploaded_image


def _uploaded_image(*, width, height, image_format="JPEG"):
    buffer = BytesIO()
    Image.new("RGB", (width, height), color="red").save(buffer, format=image_format)
    return SimpleUploadedFile(
        f"test.{image_format.lower()}", buffer.getvalue(), f"image/{image_format.lower()}"
    )


class ResizeUploadedImageTests(SimpleTestCase):
    def test_oversized_image_is_downscaled_preserving_aspect_ratio(self):
        upload = _uploaded_image(width=3000, height=1500)

        result = resize_uploaded_image(upload, max_dimension=1600)

        resized = Image.open(result)
        self.assertEqual((resized.width, resized.height), (1600, 800))

    def test_image_within_bounds_is_returned_unchanged(self):
        upload = _uploaded_image(width=400, height=300)

        result = resize_uploaded_image(upload, max_dimension=1600)

        self.assertIs(result, upload)

    def test_invalid_image_bytes_are_returned_unchanged(self):
        upload = SimpleUploadedFile("not-an-image.png", b"not actually a png", "image/png")

        result = resize_uploaded_image(upload, max_dimension=1600)

        self.assertIs(result, upload)

    def test_empty_file_is_returned_unchanged(self):
        self.assertIsNone(resize_uploaded_image(None, max_dimension=1600))
