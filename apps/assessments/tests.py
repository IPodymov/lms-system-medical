from django.test import TestCase


class AnswerVisibilityTests(TestCase):
    def test_options_are_not_part_of_public_attempt_serializer(self):
        from apps.api.serializers import AttemptSerializer

        self.assertNotIn("options", AttemptSerializer().get_fields())
