from rest_framework import serializers

from apps.assessments.models import QuizAttempt
from apps.courses.models import CourseRun
from apps.learning.models import Enrollment
from apps.notifications.models import Notification


class CourseRunSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = CourseRun
        fields = [
            "id",
            "title",
            "course_title",
            "semester",
            "academic_year",
            "start_at",
            "end_at",
            "max_students",
        ]


class EnrollmentSerializer(serializers.ModelSerializer):
    course_run = CourseRunSerializer(read_only=True)

    class Meta:
        model = Enrollment
        fields = ["id", "course_run", "status", "progress_percent", "final_score", "enrolled_at"]


class AttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizAttempt
        fields = ["id", "attempt_number", "status", "score", "max_score", "passed", "submitted_at"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "type", "title", "body", "is_read", "created_at"]
