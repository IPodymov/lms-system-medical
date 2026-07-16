from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from apps.assessments.models import Quiz, QuizAttempt
from apps.assessments.permissions import can_take_quiz
from apps.assessments.services import QuizError, save_answer, start_attempt, submit_attempt
from apps.courses.models import CourseRun
from apps.learning.models import Enrollment
from apps.learning.services import EnrollmentError, enroll
from apps.notifications.models import Notification
from .serializers import AttemptSerializer, CourseRunSerializer, EnrollmentSerializer, NotificationSerializer
class MeView(APIView):
    def get(self,request): return Response({"id":str(request.user.id),"email":request.user.email,"name":request.user.get_full_name()})
class CourseCatalogView(generics.ListAPIView):
    serializer_class=CourseRunSerializer; queryset=CourseRun.objects.filter(status="active",course__status="published").select_related("course")
class EnrollmentView(generics.ListCreateAPIView):
    serializer_class=EnrollmentSerializer
    def get_queryset(self): return Enrollment.objects.filter(user=self.request.user).select_related("course_run__course")
    def create(self,request,*args,**kwargs):
        try: item=enroll(course_run=get_object_or_404(CourseRun,pk=request.data.get("course_run")),user=request.user)
        except EnrollmentError as exc: return Response({"detail":str(exc)},status=400)
        return Response(EnrollmentSerializer(item).data,status=201)
class ProgressView(generics.ListAPIView):
    serializer_class=EnrollmentSerializer
    def get_queryset(self): return Enrollment.objects.filter(user=self.request.user).select_related("course_run__course")
class NotificationView(generics.ListAPIView):
    serializer_class=NotificationSerializer
    def get_queryset(self): return Notification.objects.filter(user=self.request.user)
class StartAttemptView(APIView):
    def post(self,request,quiz_id):
        quiz=get_object_or_404(Quiz.objects.select_related("content_block__lesson__section"),pk=quiz_id); enrollment=get_object_or_404(Enrollment,user=request.user,course_run__course=quiz.content_block.lesson.section.course)
        try: return Response(AttemptSerializer(start_attempt(quiz=quiz,enrollment=enrollment)).data,201)
        except QuizError as exc: return Response({"detail":str(exc)},400)
class AnswerView(APIView):
    def put(self,request,attempt_id):
        attempt=get_object_or_404(QuizAttempt.objects.select_related("enrollment"),pk=attempt_id,enrollment__user=request.user)
        try: save_answer(attempt=attempt,question_id=request.data["question_id"],answer_data=request.data.get("answer_data",{}))
        except (QuizError,KeyError) as exc: return Response({"detail":str(exc)},400)
        return Response(status=204)
class SubmitView(APIView):
    def post(self,request,attempt_id):
        attempt=get_object_or_404(QuizAttempt,pk=attempt_id,enrollment__user=request.user)
        return Response(AttemptSerializer(submit_attempt(attempt=attempt)).data)
