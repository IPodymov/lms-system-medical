from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from apps.courses.models import ContentBlock
from .models import Enrollment
from .services import update_progress
@login_required
def course_learning(request,enrollment_id):
    enrollment=get_object_or_404(Enrollment.objects.select_related("course_run__course"),pk=enrollment_id)
    if enrollment.user_id != request.user.id: return HttpResponseForbidden()
    return render(request,"learning/course.html",{"enrollment":enrollment,"sections":enrollment.course_run.course.sections.prefetch_related("lessons__blocks")})
@login_required
def complete_block(request,block_id):
    block=get_object_or_404(ContentBlock,pk=block_id); enrollment=get_object_or_404(Enrollment,course_run__course=block.lesson.section.course,user=request.user)
    if request.method=="POST": update_progress(enrollment=enrollment,block=block)
    return redirect("course-learning",enrollment.pk)
