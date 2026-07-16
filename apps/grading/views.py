from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404,render
from apps.assessments.permissions import can_view_gradebook
from apps.courses.models import CourseRun
@login_required
def gradebook(request,run_id):
    run=get_object_or_404(CourseRun,pk=run_id)
    if not can_view_gradebook(request.user,run): raise PermissionDenied
    return render(request,"grading/gradebook.html",{"run":run,"enrollments":run.enrollments.select_related("user").prefetch_related("grades")})
