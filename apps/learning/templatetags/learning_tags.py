from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    return mapping.get(key)


# Тип блока -> имя иконки в components/block_icon.html.
# До этого этапа тип был неразличим: студент не знал, откроется текст,
# скачается файл или начнётся тест, пока не кликнет (паттерн Open edX).
_BLOCK_ICONS = {
    "text": "text",
    "video": "video",
    "file": "file",
    "quiz": "quiz",
}


def _block_state(block, progress, current_block) -> str:
    """Одно из: completed, current, available, locked."""
    if progress is not None and progress.status == "completed":
        return "completed"
    if current_block is not None and block.id == current_block.id:
        return "current"
    return "available" if getattr(block, "is_available", True) else "locked"


@register.inclusion_tag("components/course_outline.html")
def course_outline(blocks, progresses, current_block):
    """Собрать программу курса в дерево «раздел → тема → блок».

    View отдаёт плоский список блоков, потому что именно он нужен для
    навигации «предыдущий/следующий». Группировка для показа — работа
    представления, поэтому дерево строится здесь, а не во view: так
    контекст view остаётся прежним.

    Прогресс агрегируется на уровне раздела (паттерн Open edX): одной
    галочки «блок пройден» мало, чтобы понять, сколько осталось до конца
    раздела.
    """
    sections: list[dict] = []
    section_by_id: dict[int, dict] = {}
    lesson_by_id: dict[int, dict] = {}

    for block in blocks:
        lesson = block.lesson
        section = lesson.section

        section_data = section_by_id.get(section.id)
        if section_data is None:
            section_data = {
                "id": section.id,
                "title": section.title,
                "lessons": [],
                "total": 0,
                "done": 0,
                "has_current": False,
            }
            section_by_id[section.id] = section_data
            sections.append(section_data)

        lesson_data = lesson_by_id.get(lesson.id)
        if lesson_data is None:
            lesson_data = {"id": lesson.id, "title": lesson.title, "blocks": []}
            lesson_by_id[lesson.id] = lesson_data
            section_data["lessons"].append(lesson_data)

        progress = progresses.get(block.id)
        state = _block_state(block, progress, current_block)
        lesson_data["blocks"].append(
            {
                "id": block.id,
                "title": block.title,
                "icon": _BLOCK_ICONS.get(block.type, "text"),
                "type_label": block.get_type_display(),
                "state": state,
            }
        )

        section_data["total"] += 1
        if state == "completed":
            section_data["done"] += 1
        if state == "current":
            section_data["has_current"] = True

    for section_data in sections:
        total = section_data["total"]
        section_data["percent"] = round(section_data["done"] * 100 / total) if total else 0

    return {"sections": sections}
