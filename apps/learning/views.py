from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from apps.courses.models import ContentBlock

from .models import Enrollment
from .services import is_block_available, ordered_course_blocks, update_progress


@login_required
def course_learning(request, enrollment_id):
    enrollment = get_object_or_404(
        Enrollment.objects.select_related("course_run__course"), pk=enrollment_id
    )
    if enrollment.user_id != request.user.id:
        return HttpResponseForbidden()
    progresses = {item.content_block_id: item for item in enrollment.progresses.all()}
    completed_block_ids = {
        block_id for block_id, progress in progresses.items() if progress.status == "completed"
    }
    blocks = ordered_course_blocks(enrollment.course_run.course)
    available_blocks = []
    for block in blocks:
        block.is_available = is_block_available(
            enrollment=enrollment,
            block=block,
            blocks=blocks,
            completed_block_ids=completed_block_ids,
        )
        if block.is_available:
            available_blocks.append(block)
    try:
        current_block_id = int(request.GET.get("block", ""))
    except ValueError:
        current_block_id = None
    current_block = next(
        (block for block in available_blocks if block.id == current_block_id), None
    )
    if not current_block and available_blocks:
        current_block = next(
            (
                block
                for block in available_blocks
                if progresses.get(block.id) is None or progresses[block.id].status != "completed"
            ),
            available_blocks[-1],
        )
    current_index = available_blocks.index(current_block) if current_block else None
    return render(
        request,
        "learning/course.html",
        {
            "enrollment": enrollment,
            "blocks": blocks,
            "current_block": current_block,
            "previous_block": (
                available_blocks[current_index - 1] if current_index and current_index > 0 else None
            ),
            "next_block": (
                available_blocks[current_index + 1]
                if current_index is not None and current_index + 1 < len(available_blocks)
                else None
            ),
            "progresses": progresses,
        },
    )


@login_required
def complete_block(request, block_id):
    block = get_object_or_404(ContentBlock, pk=block_id)
    enrollment = get_object_or_404(
        Enrollment, course_run__course=block.lesson.section.course, user=request.user
    )
    if request.method == "POST":
        update_progress(enrollment=enrollment, block=block)
    return redirect("course-learning", enrollment.pk)
