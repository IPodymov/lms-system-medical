from django.test import TestCase

from apps.api.serializers import AttemptSerializer


class AnswerVisibilityTests(TestCase):
    def test_options_are_not_part_of_public_attempt_serializer(self):
        self.assertNotIn("options", AttemptSerializer().get_fields())
