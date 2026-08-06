from django.test import TestCase

from apps.courses.models import ContentBlock, CourseSection, Lesson, TextContent
from apps.learning.models import ContentProgress
from apps.learning.templatetags.learning_tags import course_outline
from apps.test_helpers import CourseFixture


class CourseOutlineTagTests(TestCase):
    def setUp(self):
        fixture = CourseFixture.create()
        self.course = fixture["course"]
        self.section = fixture["section"]
        self.lesson = fixture["lesson"]
        self.enrollment = fixture["enrollment"]

    def _block(self, position, *, lesson=None, block_type="text"):
        block = ContentBlock.objects.create(
            lesson=lesson or self.lesson,
            title=f"Блок {position}",
            position=position,
            type=block_type,
        )
        if block_type == "text":
            TextContent.objects.create(content_block=block, body="Текст")
        block.is_available = True
        return block

    def _outline(self, blocks, progresses=None, current=None):
        return course_outline(blocks, progresses or {}, current)["sections"]

    def test_groups_blocks_into_sections_and_lessons(self):
        first = self._block(1)
        second_lesson = Lesson.objects.create(
            section=self.section, title="Тема 2", position=2, is_published=True
        )
        second = self._block(1, lesson=second_lesson)

        sections = self._outline([first, second])

        self.assertEqual(len(sections), 1)
        titles = [lesson["title"] for lesson in sections[0]["lessons"]]
        self.assertEqual(titles, ["Тема 1", "Тема 2"])

    def test_separate_sections_are_kept_apart(self):
        first = self._block(1)
        other_section = CourseSection.objects.create(
            course=self.course, title="Раздел 2", position=2, is_published=True
        )
        other_lesson = Lesson.objects.create(
            section=other_section, title="Тема A", position=1, is_published=True
        )
        second = self._block(1, lesson=other_lesson)

        sections = self._outline([first, second])

        self.assertEqual([section["title"] for section in sections], ["Раздел 1", "Раздел 2"])

    def test_section_progress_is_aggregated(self):
        first = self._block(1)
        second = self._block(2)
        self._block(3)
        progresses = {}
        for block in (first, second):
            progresses[block.id] = ContentProgress.objects.create(
                enrollment=self.enrollment, content_block=block, status="completed"
            )

        sections = self._outline([first, second, ContentBlock.objects.get(position=3)], progresses)

        self.assertEqual(sections[0]["done"], 2)
        self.assertEqual(sections[0]["total"], 3)
        self.assertEqual(sections[0]["percent"], 67)

    def test_empty_section_has_no_division_by_zero(self):
        sections = self._outline([])

        self.assertEqual(sections, [])

    def test_block_states_are_distinguished(self):
        done = self._block(1)
        current = self._block(2)
        locked = self._block(3, block_type="quiz")
        locked.is_available = False
        progresses = {
            done.id: ContentProgress.objects.create(
                enrollment=self.enrollment, content_block=done, status="completed"
            )
        }

        sections = self._outline([done, current, locked], progresses, current)
        states = [block["state"] for block in sections[0]["lessons"][0]["blocks"]]

        self.assertEqual(states, ["completed", "current", "locked"])

    def test_completed_block_stays_completed_even_when_current(self):
        """Пройденный блок не должен терять галочку из-за того, что открыт."""
        block = self._block(1)
        progresses = {
            block.id: ContentProgress.objects.create(
                enrollment=self.enrollment, content_block=block, status="completed"
            )
        }

        sections = self._outline([block], progresses, block)

        self.assertEqual(sections[0]["lessons"][0]["blocks"][0]["state"], "completed")

    def test_icon_matches_block_type(self):
        text = self._block(1)
        quiz = self._block(2, block_type="quiz")
        video = self._block(3, block_type="video")
        file_block = self._block(4, block_type="file")

        sections = self._outline([text, quiz, video, file_block])
        icons = [block["icon"] for block in sections[0]["lessons"][0]["blocks"]]

        self.assertEqual(icons, ["text", "quiz", "video", "file"])

    def test_type_label_is_available_for_screen_readers(self):
        quiz = self._block(1, block_type="quiz")

        sections = self._outline([quiz])

        self.assertEqual(sections[0]["lessons"][0]["blocks"][0]["type_label"], "Тест")
