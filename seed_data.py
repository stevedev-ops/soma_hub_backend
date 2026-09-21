import os, sys
sys.path.insert(0, '/home/steve/projects/teaching/backend')
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'somahome.settings')
django.setup()

from apps.core.models import User

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

print("Clean seed complete: Super Admins 'admin' & 'admin_hq' configured.")
