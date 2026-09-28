import os, sys
sys.path.insert(0, '/home/steve/projects/teaching/backend')
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'somahome.settings')
django.setup()

from apps.core.models import User
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

# 2. Seed verified tutors if empty
if TutorProfile.objects.count() == 0:
    TutorProfile.objects.create(
        full_name="Teacher Mercy Wanjiku",
        title="Senior CBC & Cambridge Science Specialist",
        bio="10+ years experience in hands-on science laboratories, botany, and Grade 4-8 mathematics.",
        avatar_url="https://images.unsplash.com/photo-1544717305-2782549b5136?w=150",
        curriculum_specialty=["CBC", "Cambridge"],
        subjects=["Mathematics", "Science & Technology", "Agriculture"],
        hourly_rate_kes=1500.00,
        rating=4.98,
        reviews_count=42,
        estates_covered=["Kilimani", "Kileleshwa", "Lavington", "Westlands"],
        phone_contact="+254712345678"
    )
    TutorProfile.objects.create(
        full_name="Teacher David Maina",
        title="Cambridge Stage 1-6 Literacy & Phonics Facilitator",
        bio="Passionate reading mentor specializing in dyslexic-friendly pedagogy and creative composition.",
        avatar_url="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150",
        curriculum_specialty=["Cambridge", "CBC"],
        subjects=["English Literacy", "Creative Writing", "Global Perspectives"],
        hourly_rate_kes=1800.00,
        rating=4.95,
        reviews_count=36,
        estates_covered=["Karen", "Runda", "Kitisuru", "Loresho"],
        phone_contact="+254722987654"
    )

# 3. Seed verified learning pods if empty
if LearningPod.objects.count() == 0:
    LearningPod.objects.create(
        name="Kilimani Green STEM Pod",
        estate="Kilimani, Nairobi",
        host_parent="Mama Liam",
        curriculum_code="CBC",
        grade_target="Grade 4",
        max_children=6,
        current_enrolled=4,
        meeting_days="Mon, Wed, Fri (09:00 AM - 01:00 PM)",
        monthly_share_kes=4500.00,
        description="A collaborative hands-on learning pod focusing on kitchen science labs, agriculture, and robotics.",
        focus_areas=["Science Lab", "Robotics", "Peer Math Games"]
    )
    LearningPod.objects.create(
        name="Karen Cambridge Explorers Pod",
        estate="Karen, Nairobi",
        host_parent="Mama Maya",
        curriculum_code="Cambridge",
        grade_target="Stage 2 & 3",
        max_children=5,
        current_enrolled=3,
        meeting_days="Tue, Thu (08:30 AM - 12:30 PM)",
        monthly_share_kes=5500.00,
        description="Outdoor nature study, phonics reading circles, and project-based mathematics in a serene garden compound.",
        focus_areas=["Phonics", "Nature Study", "Art & Expression"]
    )

print("Super Admin & Marketplace integrity check complete.")
