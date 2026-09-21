from django.db import models

class TutorProfile(models.Model):
    full_name = models.CharField(max_length=100)
    title = models.CharField(max_length=150, default="Certified CBC & Cambridge Educator")
    bio = models.TextField()
    avatar_url = models.CharField(max_length=255)
    curriculum_specialty = models.JSONField(default=list)
    subjects = models.JSONField(default=list)
    hourly_rate_kes = models.DecimalField(max_digits=8, decimal_places=2, default=1500.00)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=4.95)
    reviews_count = models.PositiveIntegerField(default=28)
    has_police_clearance = models.BooleanField(default=True)
    has_tsc_accreditation = models.BooleanField(default=True)
    estates_covered = models.JSONField(default=list)
    phone_contact = models.CharField(max_length=20, default="+254700123456")
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.full_name} ({self.title})"

class LearningPod(models.Model):
    name = models.CharField(max_length=150)
    estate = models.CharField(max_length=100)
    host_parent = models.CharField(max_length=100, default="Mama Liam")
    curriculum_code = models.CharField(max_length=20, default="CBC")
    grade_target = models.CharField(max_length=50, default="Grade 4")
    max_children = models.PositiveSmallIntegerField(default=6)
    current_enrolled = models.PositiveSmallIntegerField(default=4)
    meeting_days = models.CharField(max_length=150, default="Mon, Wed, Fri (09:00 AM - 01:00 PM)")
    monthly_share_kes = models.DecimalField(max_digits=8, decimal_places=2, default=4500.00)
    description = models.TextField()
    focus_areas = models.JSONField(default=list)

    def __str__(self):
        return f"{self.name} - {self.estate}"