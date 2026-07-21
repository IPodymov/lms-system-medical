from uuid import UUID


def direct_room_name(first_user_id: UUID, second_user_id: UUID) -> str:
    """Return the same valid Channels group name for both participants."""
    user_ids = sorted((first_user_id.hex, second_user_id.hex))
    return f"direct.{user_ids[0]}.{user_ids[1]}"


def course_room_name(course_run_id: UUID) -> str:
    return f"course.{course_run_id.hex}"
