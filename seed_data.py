import os, sys
sys.path.insert(0, '/home/steve/projects/teaching/backend')
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'somahome.settings')
django.setup()

from apps.core.models import User

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
    u.first_name = 'Super'
    u.last_name = 'Admin'
    u.role = 'ADMIN'
    u.is_staff = True
    u.is_superuser = True
    u.set_password('admin123')
    u.save()
    print(f"Super Admin '{uname}' configured with password 'admin123'.")

print("Super Admin seed complete.")
