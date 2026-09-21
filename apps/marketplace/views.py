from rest_framework import serializers, viewsets
from .models import TutorProfile, LearningPod

class TutorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TutorProfile
        fields = '__all__'

class LearningPodSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningPod
        fields = '__all__'

class TutorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TutorProfile.objects.filter(is_available=True)
    serializer_class = TutorProfileSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        estate = self.request.query_params.get('estate')
        curriculum = self.request.query_params.get('curriculum')
        if estate:
            qs = qs.filter(estates_covered__icontains=estate)
        return qs

class LearningPodViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LearningPod.objects.all()
    serializer_class = LearningPodSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        estate = self.request.query_params.get('estate')
        if estate:
            qs = qs.filter(estate__icontains=estate)
        return qs