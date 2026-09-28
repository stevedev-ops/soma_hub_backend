import os, sys
sys.path.insert(0, '/home/steve/projects/teaching/backend')
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'somahome.settings')
django.setup()

from apps.core.models import User, Student

# Ensure Super Admin exists
admin_user, _ = User.objects.get_or_create(
    username='admin',
    defaults={
        'first_name': 'Super',
        'last_name': 'Admin',
        'email': 'admin@somahome.co.ke',
        'role': 'ADMIN',
        'is_staff': True,
        'is_superuser': True
    }
)
admin_user.is_staff = True
admin_user.is_superuser = True
admin_user.role = 'ADMIN'
admin_user.set_password('admin2026')
admin_user.save()

hq_user, _ = User.objects.get_or_create(
    username='admin_hq',
    defaults={
        'first_name': 'SomaHome',
        'last_name': 'Operations HQ',
        'email': 'hq@somahome.co.ke',
        'role': 'ADMIN',
        'is_staff': True,
        'is_superuser': True
    }
)
hq_user.is_staff = True
hq_user.is_superuser = True
hq_user.role = 'ADMIN'
hq_user.set_password('admin2026')
hq_user.save()

# Ensure default Parent & Student exist
parent_user = User.objects.filter(phone_number='0722123456').first()
if not parent_user:
    parent_user = User.objects.create(
        username='mama_liam',
        first_name='Mercy',
        last_name='Njeri',
        email='mercy@somahome.co.ke',
        phone_number='0722123456',
        role='PARENT',
        estate='Kilimani, Nairobi'
    )
    parent_user.set_password('parent2026')
    parent_user.save()

student_liam = Student.objects.filter(parent=parent_user).first()
if not student_liam:
    student_liam = Student.objects.create(
        parent=parent_user,
        first_name='Liam',
        last_name='Kariuki',
        grade_level='Grade 4',
        curriculum_code='CBC',
        pin_code='4455'
    )

print("Clean seed complete: Super Admins, Parent Mercy, and Learner Liam configured.")
