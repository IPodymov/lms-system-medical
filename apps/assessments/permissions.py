from apps.courses.models import CourseAuthor, CourseRunStaff
def can_edit_course(user, course): return user.is_superuser or CourseAuthor.objects.filter(course=course,user=user).exists()
def can_manage_course_run(user, run): return can_edit_course(user,run.course) or CourseRunStaff.objects.filter(course_run=run,user=user).exists()
def can_view_course(user, course): return course.status=="published" or can_edit_course(user,course)
def can_enroll(user, run): return not user.is_anonymous and can_view_course(user,run.course)
def can_take_quiz(user, enrollment, quiz): return enrollment.user_id==user.id and enrollment.course_run.course_id==quiz.content_block.lesson.section.course_id
def can_view_attempt(user, attempt): return attempt.enrollment.user_id==user.id or can_manage_course_run(user,attempt.enrollment.course_run)
def can_grade_student(user, enrollment): return can_manage_course_run(user,enrollment.course_run)
def can_view_gradebook(user, run): return can_manage_course_run(user,run)
