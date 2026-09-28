import os, sys
sys.path.insert(0, '/home/steve/projects/teaching/backend')
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'somahome.settings')
django.setup()

from apps.core.models import User

# Ensure Super Admin exists without touching any other user data
admin_user, created = User.objects.get_or_create(
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

if not admin_user.is_superuser:
    admin_user.is_staff = True
    admin_user.is_superuser = True
    admin_user.role = 'ADMIN'
    admin_user.save()

print("Super Admin check complete. User database preserved without reseeding.")
