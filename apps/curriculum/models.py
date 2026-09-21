from django.db import models

class Curriculum(models.Model):
    code = models.CharField(max_length=20, unique=True) # CBC, CAMBRIDGE, ACE, IB, MONTESSORI
    name = models.CharField(max_length=100)
    tagline = models.CharField(max_length=200, blank=True)
    description = models.TextField()

    def __str__(self):
        return self.name

class CurriculumFramework(models.Model):
    framework_id = models.CharField(max_length=50, unique=True) # kicd_cbc, cambridge_primary, ib_pyp, montessori_primary
    name = models.CharField(max_length=150)
    organization = models.CharField(max_length=150, default="Global Open Curriculum Initiative")
    version = models.CharField(max_length=20, default="2026.1")
    schema_json = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.framework_id})"

class CreatorTemplate(models.Model):
    template_id = models.CharField(max_length=50, unique=True)
    creator_name = models.CharField(max_length=150)
    creator_handle = models.CharField(max_length=100) # @mamateaches_ke
    social_platform = models.CharField(max_length=100, default="TikTok & Instagram")
    creator_avatar = models.CharField(max_length=255, blank=True)
    creator_bio = models.TextField(blank=True)
    title = models.CharField(max_length=200)
    curriculum_code = models.CharField(max_length=50, default="CBC")
    grade_level = models.CharField(max_length=50, default="Grade 4")
    tagline = models.CharField(max_length=255, blank=True)
    sample_week_theme = models.CharField(max_length=200, blank=True)
    highlights = models.JSONField(default=list)
    sample_lessons = models.JSONField(default=list)
    imports_count = models.PositiveIntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    affiliate_commission_kes = models.DecimalField(max_digits=8, decimal_places=2, default=1500.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} by {self.creator_handle}"

class AffiliateConversion(models.Model):
    creator_handle = models.CharField(max_length=100)
    parent_name = models.CharField(max_length=150, blank=True)
    parent_phone = models.CharField(max_length=20, blank=True)
    template_id = models.CharField(max_length=50, blank=True)
    commission_kes = models.DecimalField(max_digits=8, decimal_places=2, default=1500.00)
    status = models.CharField(max_length=30, default="Credited") # Credited, Paid Out
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.creator_handle} - KES {self.commission_kes} ({self.status})"

class TeacherAvailabilitySlot(models.Model):
    teacher_id = models.CharField(max_length=50, default="mercy")
    day = models.CharField(max_length=20) # Monday..Friday
    start_time = models.CharField(max_length=20) # 09:00 AM
    end_time = models.CharField(max_length=20) # 11:00 AM
    title = models.CharField(max_length=150)
    slot_type = models.CharField(max_length=30, default="pod") # pod, one_on_one, open_booking
    target_group = models.CharField(max_length=150, default="Estate Pod")
    max_learners = models.PositiveSmallIntegerField(default=6)
    booked_learners = models.PositiveSmallIntegerField(default=0)
    hourly_rate_kes = models.DecimalField(max_digits=8, decimal_places=2, default=1500.00)
    status = models.CharField(max_length=30, default="Available")
    location = models.CharField(max_length=150, default="Physical Pod & Virtual")
    live_link = models.CharField(max_length=255, default="https://meet.jit.si/somahome-live")

    def __str__(self):
        return f"{self.day} {self.start_time}: {self.title}"

class TermPackage(models.Model):
    curriculum = models.ForeignKey(Curriculum, on_delete=models.CASCADE, related_name='packages')
    grade_level = models.CharField(max_length=50)
    term = models.PositiveSmallIntegerField(default=1)
    academic_year = models.PositiveIntegerField(default=2026)
    title = models.CharField(max_length=150)
    subtitle = models.CharField(max_length=255, blank=True)
    price_kes = models.DecimalField(max_digits=10, decimal_places=2, default=6500.00)
    badge = models.CharField(max_length=50, default='Complete Homeschool-in-a-Box')
    is_active = models.BooleanField(default=True)
    features = models.JSONField(default=list)

    def __str__(self):
        return f'{self.title} - KES {self.price_kes}'

class WeekModule(models.Model):
    term_package = models.ForeignKey(TermPackage, on_delete=models.CASCADE, related_name='weeks')
    week_number = models.PositiveSmallIntegerField()
    theme_title = models.CharField(max_length=150)
    learning_outcomes = models.JSONField(default=list)
    printable_pack_title = models.CharField(max_length=150, default='Week Consolidated Printable Pack (PDF)')
    page_count = models.PositiveSmallIntegerField(default=12)

    def __str__(self):
        return f'{self.term_package.title} - Week {self.week_number}: {self.theme_title}'

class DailyLessonGuide(models.Model):
    DAY_CHOICES = (
        (1, 'Monday'),
        (2, 'Tuesday'),
        (3, 'Wednesday'),
        (4, 'Thursday'),
        (5, 'Friday'),
    )
    week = models.ForeignKey(WeekModule, on_delete=models.CASCADE, related_name='lessons')
    day_number = models.PositiveSmallIntegerField(choices=DAY_CHOICES)
    subject = models.CharField(max_length=100)
    time_slot = models.CharField(max_length=50, default='08:30 AM - 09:15 AM')
    duration_minutes = models.PositiveIntegerField(default=35)
    
    topic = models.CharField(max_length=150)
    parent_script = models.TextField(help_text='Exact script the parent reads aloud to the child')
    learning_objective = models.TextField()
    local_materials = models.JSONField(default=list)
    step_by_step_activity = models.TextField()
    worksheet_name = models.CharField(max_length=150, default='Worksheet #1')
    
    is_lab_practical = models.BooleanField(default=False)
    has_photo_submission = models.BooleanField(default=False)

    class Meta:
        ordering = ['day_number', 'id']

    def __str__(self):
        return f'Week {self.week.week_number} Day {self.day_number}: {self.subject} - {self.topic}'
