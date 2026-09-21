from rest_framework import serializers
from .models import Curriculum, TermPackage, WeekModule, DailyLessonGuide

class DailyLessonGuideSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyLessonGuide
        fields = '__all__'

class WeekModuleSerializer(serializers.ModelSerializer):
    lessons = DailyLessonGuideSerializer(many=True, read_only=True)
    class Meta:
        model = WeekModule
        fields = '__all__'

class TermPackageSerializer(serializers.ModelSerializer):
    curriculum_name = serializers.CharField(source='curriculum.name', read_only=True)
    curriculum_code = serializers.CharField(source='curriculum.code', read_only=True)
    weeks = WeekModuleSerializer(many=True, read_only=True)

    class Meta:
        model = TermPackage
        fields = '__all__'

class CurriculumSerializer(serializers.ModelSerializer):
    packages = TermPackageSerializer(many=True, read_only=True)
    class Meta:
        model = Curriculum
        fields = '__all__'