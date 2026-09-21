import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'somahome.settings')
django.setup()

from apps.core.models import User, Student
from apps.curriculum.models import Curriculum, TermPackage, WeekModule, DailyLessonGuide
from apps.tracker.models import Enrollment, DailyLessonLog, ProjectSubmission
from apps.marketplace.models import TutorProfile, LearningPod
from apps.payments.models import MpesaTransaction

print("Seeding SomaHome Kenya database...")

# 1. Create Demo Parent & Students
parent, _ = User.objects.get_or_create(
    username="steve_parent",
    defaults={
        "first_name": "Steve",
        "last_name": "Kariuki",
        "email": "steve@somahome.co.ke",
        "phone_number": "+254712345678",
        "role": "PARENT",
        "estate": "Kilimani, Nairobi"
    }
)
parent.set_password("homeschool2026")
parent.save()

student_liam, _ = Student.objects.get_or_create(
    parent=parent,
    first_name="Liam",
    defaults={
        "last_name": "Kariuki",
        "grade_level": "Grade 4",
        "curriculum_code": "CBC",
        "avatar_url": "https://images.unsplash.com/photo-1544717305-2782549b5136?w=150"
    }
)

student_maya, _ = Student.objects.get_or_create(
    parent=parent,
    first_name="Maya",
    defaults={
        "last_name": "Kariuki",
        "grade_level": "Year 5",
        "curriculum_code": "CAMBRIDGE",
        "avatar_url": "https://images.unsplash.com/photo-1517677208171-0bc6725a3e60?w=150"
    }
)

# 2. Curricula
cbc, _ = Curriculum.objects.get_or_create(
    code="CBC",
    defaults={
        "name": "Kenya Competency-Based Curriculum (CBC)",
        "tagline": "Practical, value-driven, KICD-aligned learning for Kenyan families",
        "description": "Tailored for Kenyan homeschoolers with strands, sub-strands, and home-friendly community practicals."
    }
)

cambridge, _ = Curriculum.objects.get_or_create(
    code="CAMBRIDGE",
    defaults={
        "name": "Cambridge International Primary (UK)",
        "tagline": "Global gold-standard curriculum preparing learners for IGCSE",
        "description": "Structured English, Mathematics, and Science frameworks with checkpoints and global benchmarks."
    }
)

ace, _ = Curriculum.objects.get_or_create(
    code="ACE",
    defaults={
        "name": "Accelerated Christian Education (A.C.E.)",
        "tagline": "Character-building mastery learning with PACE workbooks",
        "description": "Individualized, self-paced curriculum with character traits and biblical values integration."
    }
)

# 3. Term Packages
pkg_g4_cbc, _ = TermPackage.objects.get_or_create(
    curriculum=cbc,
    grade_level="Grade 4",
    term=1,
    defaults={
        "academic_year": 2026,
        "title": "Grade 4 Term 1 — Complete Homeschool-in-a-Box",
        "subtitle": "Everything you need for 12 weeks: daily 3-hour guides, weekly printables, kitchen science labs & CBC report card.",
        "price_kes": 6500.00,
        "badge": "Most Popular in Nairobi",
        "is_active": True,
        "features": [
            "Zero-prep daily parent scripts (word-for-word instructions)",
            "12 consolidated Sunday printable worksheet packs",
            "Science & Agriculture experiments using everyday Kenyan materials",
            "Official KICD-aligned CBC Rubric Report Card (EE, ME, AE, BE)",
            "Dedicated WhatsApp Facilitator for marking & guidance",
            "Access to local estate learning pods"
        ]
    }
)

pkg_y5_cambridge, _ = TermPackage.objects.get_or_create(
    curriculum=cambridge,
    grade_level="Year 5",
    term=1,
    defaults={
        "academic_year": 2026,
        "title": "Year 5 Term 1 — Cambridge Primary Complete Box",
        "subtitle": "Rigorous UK Stage 5 preparation for Cambridge Checkpoint in English, Math, and Science.",
        "price_kes": 8500.00,
        "badge": "International Benchmark",
        "is_active": True,
        "features": [
            "Weekly diagnostic checkpoint quizzes",
            "Hands-on STEM and investigative science guides",
            "Comprehensive reading comprehension anthologies",
            "Official Cambridge transcript builder"
        ]
    }
)

# 4. Week Modules & Lessons for Grade 4 CBC
w3, _ = WeekModule.objects.get_or_create(
    term_package=pkg_g4_cbc,
    week_number=3,
    defaults={
        "theme_title": "Environmental Cleanliness, Fractions & Matter",
        "learning_outcomes": ["Perform safe water purification", "Divide objects into fractional parts", "Use descriptive adverbs in storytelling"],
        "printable_pack_title": "Grade 4 Term 1 - Week 3 Complete Printable Pack (PDF)",
        "page_count": 14
    }
)

# Daily Lessons for Week 3
DailyLessonGuide.objects.all().delete() # refresh cleanly

l1 = DailyLessonGuide.objects.create(
    week=w3,
    day_number=1, # Monday
    subject="Mathematics Activities",
    time_slot="08:30 AM - 09:15 AM",
    duration_minutes=35,
    topic="Fractions: Halves, Quarters & Eighths",
    learning_objective="Learners should identify and represent proper fractions using concrete everyday objects.",
    parent_script="Greet your child and say: 'Today we are dividing a delicious chapati among our family members! If we have one whole round chapati and slice it straight down the middle, how many equal slices do we have? That is 1/2.'",
    local_materials=["Round cardboard or paper plate", "Pair of safety scissors", "Ruler and pencil"],
    step_by_step_activity="1. Have the child fold the round plate exactly in half and color one side blue (1/2).\n2. Fold again into quarters and label each slice 1/4.\n3. Complete Worksheet #1 by shading the fractions shown.",
    worksheet_name="Math_G4_W3_Fractions_Plate.pdf",
    is_lab_practical=False
)

l2 = DailyLessonGuide.objects.create(
    week=w3,
    day_number=2, # Tuesday
    subject="English Language & Literacy",
    time_slot="09:30 AM - 10:15 AM",
    duration_minutes=35,
    topic="Descriptive Writing: The Animals of Tsavo",
    learning_objective="Compose a 4-sentence descriptive paragraph utilizing dynamic adjectives (majestic, dusty, swift).",
    parent_script="Say: 'Imagine we just arrived at Tsavo National Park under the warm Kenyan sun. Look at the red elephant throwing dust over its back! What words describe how the elephant looks and moves?'",
    local_materials=["Lined exercise book or printed worksheet", "Colored pencils"],
    step_by_step_activity="1. Read the short passage on Worksheet #2 together.\n2. Circle 5 descriptive adjectives.\n3. Child writes 4 sentences describing their favorite African animal.",
    worksheet_name="English_G4_W3_Tsavo_Safari.pdf",
    is_lab_practical=False
)

l3 = DailyLessonGuide.objects.create(
    week=w3,
    day_number=3, # Wednesday (Today's Highlight Lab!)
    subject="Science & Technology (Home Lab)",
    time_slot="08:30 AM - 09:30 AM",
    duration_minutes=45,
    topic="Water Purification with Local Materials",
    learning_objective="Construct a working mechanical water filtration apparatus demonstrating how sediment and charcoal filter muddy water.",
    parent_script="Say: 'When it rains heavily and our rivers turn brown with mud, how can communities make water clear again? Today, you are an environmental engineer! We are going to build our very own filter using things from our kitchen and compound.'",
    local_materials=[
        "1 empty plastic soda bottle (e.g. Dasani or Quencher)",
        "Charcoal pieces crushed from the jiko",
        "Clean fine sand from the compound",
        "Small clean pebbles / gravel",
        "Cotton wool or a piece of clean cotton cloth",
        "A cup of muddy/dirty water"
    ],
    step_by_step_activity="1. Cut the bottom third off the plastic bottle using scissors.\n2. Invert the top neck-down into a glass.\n3. Layer from bottom to top: cotton cloth, crushed charcoal, fine sand, then small pebbles.\n4. Pour the muddy water slowly into the top.\n5. Observe clear water dripping into the cup below!\n6. Take a photo and upload to your SomaHome student portfolio.",
    worksheet_name="Science_G4_W3_Water_Filter_Lab.pdf",
    is_lab_practical=True,
    has_photo_submission=True
)

l4 = DailyLessonGuide.objects.create(
    week=w3,
    day_number=4, # Thursday
    subject="Kiswahili Lugha na Kusoma",
    time_slot="09:00 AM - 09:40 AM",
    duration_minutes=35,
    topic="Ngeli ya A-WA na Methali za Mazingira",
    learning_objective="Kutambua nomino katika ngeli ya A-WA na kutumia methali 'Maji yakimwagika hayazoleki'.",
    parent_script="Mwambie mwanafunzi: 'Leo tunajifunza kuhusu viumbe vilivyo hai katika ngeli ya A-WA. Mtoto analala, watoto wanalala. Kipepeo anaruka, vipepeo wanaruka.'",
    local_materials=["Daftari ya Kiswahili", "Picha za wanyama na watu"],
    step_by_step_activity="1. Soma hadithi fupi ukurasa wa 3 kwenye kijitabu chetu.\n2. Badilisha sentensi tano kutoka umoja hadi wingi.\n3. Jadili maana ya methali ya leo.",
    worksheet_name="Kiswahili_G4_W3_Ngeli_AWA.pdf",
    is_lab_practical=False
)

l5 = DailyLessonGuide.objects.create(
    week=w3,
    day_number=5, # Friday
    subject="Agriculture & Nutrition",
    time_slot="10:00 AM - 10:45 AM",
    duration_minutes=40,
    topic="Kitchen Gardening with Recycled Containers",
    learning_objective="Prepare seedling potting mix and transplant sukuma wiki or spinach seedlings into a plastic container.",
    parent_script="Say: 'Good morning farmer! Today we are planting our own fresh vegetables so we can eat healthy sukuma wiki straight from our balcony or backyard.'",
    local_materials=[
        "1 recycled 5-litre cooking oil container or milk carton",
        "Rich black garden soil mixed with compost",
        "Sukuma wiki (collard greens) seedlings or tomato seeds",
        "Watering can or plastic bottle with holes in the cap"
    ],
    step_by_step_activity="1. Poke 4 drainage holes at the bottom of your plastic container.\n2. Fill with rich soil leaving 2 inches from the top.\n3. Plant 2 sukuma wiki seedlings gently and pat soil around roots.\n4. Water gently and place in sunlight.",
    worksheet_name="Agri_G4_W3_Kitchen_Garden.pdf",
    is_lab_practical=True,
    has_photo_submission=True
)

# 5. Student Enrollment & Existing Submissions
enrollment_liam, _ = Enrollment.objects.get_or_create(
    student=student_liam,
    term_package=pkg_g4_cbc,
    defaults={
        "is_paid": True,
        "assigned_mentor": "Teacher Mercy Wanjiku (Senior CBC Facilitator)"
    }
)

ProjectSubmission.objects.all().delete()
ProjectSubmission.objects.create(
    enrollment=enrollment_liam,
    lesson=l3,
    title="Liam's Working Charcoal Water Filter",
    photo_url="https://images.unsplash.com/photo-1544717305-2782549b5136?w=600",
    description="I layered cotton, charcoal from our jiko, and river sand. The muddy water turned almost completely clear! Science is awesome.",
    local_materials_used="Plastic bottle, jiko charcoal, compound sand, cotton fabric",
    rubric_score="EE",
    mentor_feedback="Superb scientific initiative Liam! The density layering was executed accurately. Demonstrates high Level 4 competency in Environmental Hygiene."
)

ProjectSubmission.objects.create(
    enrollment=enrollment_liam,
    lesson=l5,
    title="Recycled Container Sukuma Wiki Potting",
    photo_url="https://images.unsplash.com/photo-1592417817098-8f3d6910985c?w=600",
    description="Planted 3 sukuma wiki seedlings in an empty 5L cooking oil gallon. We water them every morning at 8:00 AM.",
    local_materials_used="5L plastic cooking oil container, compost, sukuma wiki seedlings",
    rubric_score="EE",
    mentor_feedback="Remarkable application of agriculture principles and environmental conservation through reuse."
)

# 6. Marketplace: Vetted Tutors in Nairobi
TutorProfile.objects.all().delete()
TutorProfile.objects.create(
    full_name="Teacher Mercy Wanjiku",
    title="Lead CBC Facilitator & Primary STEM Specialist",
    bio="Over 9 years experience coaching homeschooling families across Kilimani, Lavington, and Karen. Passionate about hands-on science and making math engaging without anxiety.",
    avatar_url="https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=300",
    curriculum_specialty=["CBC (Grades 1-8)", "Montessori Primary"],
    subjects=["Mathematics", "Integrated Science & Tech", "Agriculture", "Kiswahili"],
    hourly_rate_kes=1500.00,
    rating=4.96,
    reviews_count=42,
    has_police_clearance=True,
    has_tsc_accreditation=True,
    estates_covered=["Kilimani", "Kileleshwa", "Lavington", "Karen", "Ngong Road"],
    phone_contact="+254722889900",
    is_available=True
)

TutorProfile.objects.create(
    full_name="Mwalimu David Otieno",
    title="Cambridge Checkpoint & IGCSE Mathematics Coach",
    bio="Former senior teacher at a premier Nairobi international school. Specializes in transforming struggling students into confident A* candidates in Cambridge Key Stages 2, 3 and IGCSE.",
    avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=300",
    curriculum_specialty=["Cambridge Primary & Lower Secondary", "Pearson Edexcel"],
    subjects=["Mathematics", "Physics", "Coding & Scratch"],
    hourly_rate_kes=2000.00,
    rating=4.98,
    reviews_count=35,
    has_police_clearance=True,
    has_tsc_accreditation=True,
    estates_covered=["Syokimau", "South B", "South C", "Langata", "Kitengela"],
    phone_contact="+254733112233",
    is_available=True
)

TutorProfile.objects.create(
    full_name="Madam Grace Nduta",
    title="Early Years, Phonics & Neurodiversity Specialist",
    bio="Trained in phonics, dyslexia, and ADHD accommodations. Helps young learners fall in love with reading and structured inquiry.",
    avatar_url="https://images.unsplash.com/photo-1580489944761-15a19d654956?w=300",
    curriculum_specialty=["CBC PP1-Grade 3", "Cambridge Early Years", "A.C.E. Reading"],
    subjects=["Jolly Phonics", "Early Reading", "Art & Craft", "Life Skills"],
    hourly_rate_kes=1600.00,
    rating=4.94,
    reviews_count=29,
    has_police_clearance=True,
    has_tsc_accreditation=True,
    estates_covered=["Runda", "Kitisuru", "Westlands", "Gigiri", "Ruaka"],
    phone_contact="+254711445566",
    is_available=True
)

# 7. Neighborhood Learning Pods
LearningPod.objects.all().delete()
LearningPod.objects.create(
    name="Syokimau Grade 4 CBC Explorers Pod",
    estate="Syokimau (Mwananchi Road)",
    host_parent="Mama Liam (Syokimau Court 4)",
    curriculum_code="CBC",
    grade_target="Grade 4",
    max_children=6,
    current_enrolled=4,
    meeting_days="Mon, Wed, Fri (09:00 AM - 01:00 PM)",
    monthly_share_kes=4500.00,
    description="A warm, secure neighborhood homeschool pod sharing a vetted CBC science & math tutor. Spacious backyard for physical games and agriculture projects.",
    focus_areas=["Hands-on Science Labs", "Mental Math Challenges", "Taekwondo & Sports"]
)

LearningPod.objects.create(
    name="Kilimani Cambridge STEM & Coding Hub",
    estate="Kilimani (Dennis Pritt)",
    host_parent="Dr. Amina Patel",
    curriculum_code="CAMBRIDGE",
    grade_target="Year 4-6",
    max_children=5,
    current_enrolled=3,
    meeting_days="Tue & Thu (10:00 AM - 02:00 PM)",
    monthly_share_kes=6000.00,
    description="Focused on Cambridge Stage 5 science labs, Lego robotics, and collaborative group discussions. High-speed fibre internet and outdoor garden.",
    focus_areas=["Robotics & Coding", "Cambridge Science Practicals", "Creative Writing"]
)

LearningPod.objects.create(
    name="Karen Nature & Forest Homeschool Co-op",
    estate="Karen (Mbagathi Way)",
    host_parent="Mrs. Njeri Hamilton",
    curriculum_code="CBC",
    grade_target="All Grades (Mixed Ages)",
    max_children=10,
    current_enrolled=8,
    meeting_days="Every Friday (09:30 AM - 03:00 PM)",
    monthly_share_kes=3500.00,
    description="Weekly nature walks, birdwatching, environmental stewardship, horse riding basics, and drama club for Nairobi homeschoolers.",
    focus_areas=["Outdoor Biology", "Public Speaking & Drama", "Swimming & Athletics"]
)

print("SomaHome database populated with rich, authentic Kenyan homeschool data!")