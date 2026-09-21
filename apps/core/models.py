from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('PARENT', 'Parent'),
        ('STUDENT', 'Student'),
        ('TUTOR', 'Tutor'),
        ('CREATOR', 'Creator'),
        ('ADMIN', 'Admin'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='PARENT')
    phone_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    estate = models.CharField(max_length=100, blank=True, default='Kilimani, Nairobi')
    bio = models.TextField(blank=True, default='')

    def __str__(self):
        return f'{self.username} ({self.role})'

class Student(models.Model):
    parent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='students')
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50, blank=True, default='')
    username = models.CharField(max_length=60, blank=True, default='')
    pin_code = models.CharField(max_length=10, default='1234')
    date_of_birth = models.DateField(null=True, blank=True)
    grade_level = models.CharField(max_length=50, default='Grade 4')
    curriculum_code = models.CharField(max_length=20, default='CBC')
    avatar_url = models.CharField(max_length=255, blank=True, default='https://images.unsplash.com/photo-1544717305-2782549b5136?w=150')

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.grade_level} {self.curriculum_code})'
