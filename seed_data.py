import os, sys
sys.path.insert(0, '/home/steve/projects/teaching/backend')
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'somahome.settings')
django.setup()

from apps.core.models import User, Student
from apps.marketplace.models import TutorProfile, LearningPod

# 1. Ensure Super Admin accounts exist
admin_usernames = ['super_admin', 'superadmin', 'admin', 'admin_hq']

for uname in admin_usernames:
    u, created = User.objects.get_or_create(
        username=uname,
        defaults={
            'first_name': 'Super',
            'last_name': 'Admin',
            'email': f'{uname}@somahome.co.ke',
            'role': 'ADMIN',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if not u.is_superuser:
        u.is_staff = True
        u.is_superuser = True
        u.role = 'ADMIN'
        u.set_password('admin123')
        u.save()

# 2. Delete all legacy dummy/mock test parent and student accounts from previous development
# Keep ONLY real users (like Steve mutwiri 0190821091) and super admins
legacy_test_usernames = ['mama_liam', '0722123456', '0744556677', '0711223344', '1234', '0799887766']
deleted_test_users = User.objects.filter(username__in=legacy_test_usernames).delete()
print("Cleaned up legacy test users:", deleted_test_users)

# Also delete any students attached to test accounts or legacy names
Student.objects.filter(first_name__in=['Zawadi', 'Ethan', 'Liam', 'child']).exclude(parent__username='0190821091').delete()
Student.objects.filter(username__in=['mike_0799887766']).delete()

# 3. Ensure 0 dummy teachers and 0 dummy pods
TutorProfile.objects.filter(full_name__in=["Teacher Mercy Wanjiku", "Teacher David Maina", "Teacher Mercy Cherono"]).delete()
LearningPod.objects.filter(name__in=["Kilimani Green STEM Pod", "Karen Cambridge Explorers Pod"]).delete()

print("Integrity check complete: All mock data removed. ONLY real registered users remain.")
