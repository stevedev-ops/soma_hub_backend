from rest_framework import serializers
from .models import Enrollment, DailyLessonLog, ProjectSubmission
from apps.curriculum.serializers import DailyLessonGuideSerializer

class ProjectSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectSubmission
        fields = '__all__'

class DailyLessonLogSerializer(serializers.ModelSerializer):
    lesson_details = DailyLessonGuideSerializer(source='lesson', read_only=True)
    class Meta:
        model = DailyLessonLog
        fields = '__all__'

class EnrollmentSerializer(serializers.ModelSerializer):
    projects = ProjectSubmissionSerializer(many=True, read_only=True)
    logs = DailyLessonLogSerializer(many=True, read_only=True)
    student_name = serializers.CharField(source='student.first_name', read_only=True)
    package_title = serializers.CharField(source='term_package.title', read_only=True)

    class Meta:
        model = Enrollment
        fields = '__all__'