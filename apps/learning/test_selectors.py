from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.courses.models import ContentBlock, CourseRun, TextContent
from apps.learning.models import ContentProgress, Enrollment
from apps.learning.selectors import with_block_counts
from apps.test_helpers import CourseFixture


class WithBlockCountsTests(TestCase):
    def setUp(self):
        fixture = CourseFixture.create()
        self.user = fixture["user"]
        self.course = fixture["course"]
        self.section = fixture["section"]
        self.lesson = fixture["lesson"]
        self.enrollment = fixture["enrollment"]

    def _block(self, position: int, *, required: bool = True) -> ContentBlock:
        block = ContentBlock.objects.create(
            lesson=self.lesson,
            title=f"Блок {position}",
            position=position,
            type="text",
            is_required=required,
        )
        TextContent.objects.create(content_block=block, body="Текст")
        return block

    def _annotated(self) -> Enrollment:
        return with_block_counts(Enrollment.objects.filter(pk=self.enrollment.pk)).get()

    def test_counts_are_zero_without_blocks(self):
        result = self._annotated()

        self.assertEqual(result.blocks_total, 0)
        self.assertEqual(result.blocks_done, 0)

    def test_counts_required_published_blocks(self):
        self._block(1)
        self._block(2)

        result = self._annotated()

        self.assertEqual(result.blocks_total, 2)
        self.assertEqual(result.blocks_done, 0)

    def test_completed_blocks_are_counted(self):
        first = self._block(1)
        self._block(2)
        ContentProgress.objects.create(
            enrollment=self.enrollment, content_block=first, status="completed"
        )

        result = self._annotated()

        self.assertEqual(result.blocks_total, 2)
        self.assertEqual(result.blocks_done, 1)

    def test_unfinished_progress_is_not_counted_as_done(self):
        first = self._block(1)
        ContentProgress.objects.create(
            enrollment=self.enrollment, content_block=first, status="in_progress"
        )

        result = self._annotated()

        self.assertEqual(result.blocks_done, 0)

    def test_optional_block_is_excluded_from_the_total(self):
        self._block(1)
        self._block(2, required=False)

        result = self._annotated()

        self.assertEqual(result.blocks_total, 1)

    def test_unpublished_lesson_is_excluded_from_the_total(self):
        self._block(1)
        self.lesson.is_published = False
        self.lesson.save(update_fields=["is_published"])

        result = self._annotated()

        self.assertEqual(result.blocks_total, 0)

    def test_unpublished_section_is_excluded_from_the_total(self):
        self._block(1)
        self.section.is_published = False
        self.section.save(update_fields=["is_published"])

        result = self._annotated()

        self.assertEqual(result.blocks_total, 0)

    def test_counts_do_not_multiply_across_joins(self):
        """Две аннотации идут по разным путям связей.

        Без distinct=True строки перемножаются на соединении, и оба счётчика
        растут пропорционально друг другу: три блока и два завершения дали бы
        6 и 6 вместо 3 и 2.
        """
        first = self._block(1)
        second = self._block(2)
        self._block(3)
        for block in (first, second):
            ContentProgress.objects.create(
                enrollment=self.enrollment, content_block=block, status="completed"
            )

        result = self._annotated()

        self.assertEqual(result.blocks_total, 3)
        self.assertEqual(result.blocks_done, 2)

    def test_list_stays_a_single_query(self):
        """Счётчики не должны превращать список курсов в N+1."""
        self._block(1)
        now = timezone.now()
        for index in range(3):
            run = CourseRun.objects.create(
                course=self.course,
                title=f"Поток {index}",
                status=CourseRun.Status.ACTIVE,
                start_at=now,
                end_at=now + timedelta(days=30),
                enrollment_start_at=now,
                enrollment_end_at=now + timedelta(days=7),
            )
            Enrollment.objects.create(course_run=run, user=self.user)

        queryset = with_block_counts(
            Enrollment.objects.filter(user=self.user).select_related("course_run__course")
        )

        with self.assertNumQueries(1):
            [(item.blocks_total, item.blocks_done) for item in queryset]
