from django.db import models
from apps.core.models import Student
from apps.curriculum.models import TermPackage, DailyLessonGuide

class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    term_package = models.ForeignKey(TermPackage, on_delete=models.CASCADE)
    is_paid = models.BooleanField(default=False)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    whatsapp_support_active = models.BooleanField(default=True)
    assigned_mentor = models.CharField(max_length=100, default='Teacher Mercy (Senior CBC Facilitator)')

    class Meta:
        unique_together = ('student', 'term_package')

    def __str__(self):
        return f'{self.student.first_name} in {self.term_package.title}'

class DailyLessonLog(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='logs')
    lesson = models.ForeignKey(DailyLessonGuide, on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False)
    completion_date = models.DateField(auto_now=True)
    comprehension_stars = models.PositiveSmallIntegerField(default=5) # 1 to 5
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'{self.enrollment.student.first_name} - {self.lesson.subject} (Completed: {self.is_completed})'

class ProjectSubmission(models.Model):
    RUBRIC_CHOICES = (
        ('EE', 'Exceeding Expectations (Level 4)'),
        ('ME', 'Meeting Expectations (Level 3)'),
        ('AE', 'Approaching Expectations (Level 2)'),
        ('BE', 'Below Expectations (Level 1)'),
    )
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='projects')
    lesson = models.ForeignKey(DailyLessonGuide, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=150)
    photo_url = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    local_materials_used = models.CharField(max_length=255, default='Plastic bottle, charcoal, fine sand, cotton')
    rubric_score = models.CharField(max_length=5, choices=RUBRIC_CHOICES, default='EE')
    mentor_feedback = models.TextField(blank=True, default='Outstanding initiative! The filtration layers were cleanly separated and clear water was achieved.')
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.title} - {self.rubric_score}'
