import os, sys
sys.path.insert(0, '/home/steve/projects/teaching/backend')
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'somahome.settings')
django.setup()

from apps.core.models import User
from apps.marketplace.models import TutorProfile, LearningPod

# 1. Ensure Super Admin accounts exist and are never deleted
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

# 2. Pure Clean State: Delete any legacy dummy/mock teachers
dummy_teachers = ["Teacher Mercy Wanjiku", "Teacher David Maina", "Teacher Mercy Cherono"]
deleted_tutors_count, _ = TutorProfile.objects.filter(full_name__in=dummy_teachers).delete()
if deleted_tutors_count > 0:
    print(f"Removed {deleted_tutors_count} dummy tutor profile(s).")

# 3. Pure Clean State: Delete any legacy dummy/mock pods
dummy_pods = ["Kilimani Green STEM Pod", "Karen Cambridge Explorers Pod"]
deleted_pods_count, _ = LearningPod.objects.filter(name__in=dummy_pods).delete()
if deleted_pods_count > 0:
    print(f"Removed {deleted_pods_count} dummy pod(s).")

print("Pure clean state enforced: 0 dummy teachers, 0 dummy pods. Super Admin ready.")
