import os, sys, json, io
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'somahome.settings')
sys.path.insert(0, '/home/steve/projects/teaching/backend')
django.setup()

from apps.curriculum.models import Curriculum, TermPackage, WeekModule, DailyLessonGuide
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

TEMPLATES_DIR = '/home/steve/projects/teaching/backend/curriculum_templates'
DOWNLOADS_DIR = '/home/steve/projects/teaching/downloads'
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

print("=== SOMA HOME FULL MULTI-TERM & HIGH SCHOOL ENGINE ===")

def generate_pdf_pack(title_header, sub_header, grade_name, curriculum_code, schedule_rows, worksheets_info, out_filename):
    out_path = os.path.join(DOWNLOADS_DIR, out_filename)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    elements = []
    styles = getSampleStyleSheet()
    
    brand_color = '#00A651' if 'CBC' in curriculum_code else ('#0284C7' if 'CAMBRIDGE' in curriculum_code else ('#D97706' if 'ACE' in curriculum_code else ('#7C3AED' if 'US' in curriculum_code else '#BE185D')))
    
    elements.append(Paragraph('SOMAHOME KENYA • UNIVERSAL HOMESCHOOL OS', ParagraphStyle('Brand', fontName='Helvetica-Bold', fontSize=18, textColor=colors.HexColor(brand_color))))
    elements.append(Paragraph(f'{title_header} • {grade_name}', ParagraphStyle('SubBrand', fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#0F172A'), spaceAfter=8)))
    elements.append(HRFlowable(width='100%', thickness=2, color=colors.HexColor(brand_color), spaceAfter=12))
    
    elements.append(Paragraph(f'<b>Weekly Homeschool Timetable & Parent Checklist ({sub_header}):</b>', styles['Heading3']))
    
    t_sched = Table(schedule_rows, colWidths=[65, 115, 180, 180])
    t_sched.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor(brand_color)),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(t_sched)
    elements.append(Spacer(1, 14))
    
    for ws in worksheets_info:
        elements.append(Paragraph(f'<b>{ws["title"]}</b>', styles['Heading4']))
        elements.append(Paragraph(f'<b>Parent/Facilitator Script:</b> <i>\"{ws["script"]}\"</i>', styles['Normal']))
        elements.append(Paragraph(f'<b>Activity & Practical:</b> {ws["activity"]}', styles['Normal']))
        elements.append(Paragraph(f'<b>Required Everyday Materials:</b> {ws["materials"]}', styles['Normal']))
        elements.append(Spacer(1, 8))
        
    doc.build(elements)
    with open(out_path, 'wb') as f:
        f.write(buffer.getvalue())
    print(f'  ✓ [PDF Generated] {out_filename} ({os.path.getsize(out_path)} bytes)')

def ingest_package(pkg_data):
    c_data = pkg_data['curriculum']
    p_data = pkg_data['term_package']
    weeks_list = pkg_data['weeks']
    
    curriculum, _ = Curriculum.objects.update_or_create(
        code=c_data['code'],
        defaults={
            'name': c_data['name'],
            'tagline': c_data.get('tagline', ''),
            'description': c_data.get('description', '')
        }
    )
    
    term_pkg, _ = TermPackage.objects.update_or_create(
        curriculum=curriculum,
        grade_level=p_data['grade_level'],
        term=p_data.get('term', 1),
        academic_year=p_data.get('academic_year', 2026),
        defaults={
            'title': p_data['title'],
            'subtitle': p_data.get('subtitle', ''),
            'price_kes': p_data.get('price_kes', 6500.0),
            'badge': p_data.get('badge', 'Complete Homeschool-in-a-Box'),
            'features': p_data.get('features', []),
            'is_active': True
        }
    )
    
    for w in weeks_list:
        week_mod, _ = WeekModule.objects.update_or_create(
            term_package=term_pkg,
            week_number=w['week_number'],
            defaults={
                'theme_title': w.get('theme_title', f'Week {w["week_number"]} Learning Module'),
                'learning_outcomes': w.get('learning_outcomes', []),
                'printable_pack_title': w.get('printable_pack_title', f'Week {w["week_number"]} Printable Pack (PDF)'),
                'page_count': w.get('page_count', 12)
            }
        )
        
        for lesson in w.get('lessons', []):
            DailyLessonGuide.objects.update_or_create(
                week=week_mod,
                day_number=lesson['day_number'],
                subject=lesson['subject'],
                defaults={
                    'time_slot': lesson.get('time_slot', '09:00 AM - 09:45 AM'),
                    'duration_minutes': lesson.get('duration_minutes', 40),
                    'topic': lesson.get('topic', 'Lesson Exploration'),
                    'parent_script': lesson.get('parent_script', 'Follow the daily guide with your child.'),
                    'learning_objective': lesson.get('learning_objective', 'Demonstrate conceptual mastery.'),
                    'local_materials': lesson.get('local_materials', []),
                    'step_by_step_activity': lesson.get('step_by_step_activity', 'Complete exercises in workbook.'),
                    'worksheet_name': lesson.get('worksheet_name', 'Worksheet #1'),
                    'is_lab_practical': lesson.get('is_lab_practical', False),
                    'has_photo_submission': lesson.get('has_photo_submission', False)
                }
            )

    print(f'  ✓ [DB Ingested] {curriculum.code}: {term_pkg.title} ({len(weeks_list)} weeks, {sum(len(w.get("lessons",[])) for w in weeks_list)} lessons)')
    return term_pkg

def make_weeks_for_term(term_num, grade_level, default_subjects):
    weeks = []
    start_week = (term_num - 1) * 12 + 1
    for i in range(1, 13):
        abs_week = start_week + i - 1
        lessons = []
        for d, sub in enumerate(default_subjects, 1):
            lessons.append({
                'day_number': d,
                'subject': sub['name'],
                'time_slot': sub['time'],
                'duration_minutes': 45,
                'topic': f'{sub["name"]} - Term {term_num} Week {i} Mastery Module',
                'parent_script': f'Introduce Term {term_num} Unit {i} with guiding questions to reinforce foundational understanding.',
                'learning_objective': f'Learner demonstrates conceptual grasp and problem-solving for Term {term_num} {sub["name"]}.',
                'local_materials': sub['materials'],
                'step_by_step_activity': f'1. Guided conceptual analysis.\n2. Work through 3 stepped exercises.\n3. Formative self-reflection.',
                'worksheet_name': f'{sub["name"]} Worksheet T{term_num}#{i}.{d}',
                'is_lab_practical': sub.get('is_lab', False),
                'has_photo_submission': sub.get('photo', False)
            })
        weeks.append({
            'week_number': i,
            'theme_title': f'Term {term_num} Week {i}: Advanced Competency & Exploration',
            'strand': f'Term {term_num} Core Applied Strands',
            'sub_strand': f'Unit {i} Milestones & Rubrics',
            'printable_pack_title': f'{grade_level} Term {term_num} Week {i} Printable Pack (PDF)',
            'page_count': 12,
            'learning_outcomes': [f'Master Term {term_num} core competencies for week {i}', 'Complete hands-on practical log'],
            'lessons': lessons
        })
    return weeks

# ==============================================================================
# TERMS 2 & 3 AND SENIOR/HIGH SCHOOL EXPANSION PACKAGES
# ==============================================================================

multi_term_configs = [
    # 1. CBC Grade 4 Term 2
    {
        'json_name': 'kicd_grade4_cbc_term2.json',
        'pdf_name': 'Grade4_CBC_Term2_Printable_Pack.pdf',
        'curriculum': {'code': 'CBC', 'name': 'Kenya Competency-Based Curriculum (CBC)', 'tagline': 'KICD Aligned', 'description': 'National curriculum approved by KICD.'},
        'term_package': {'grade_level': 'Grade 4', 'term': 2, 'academic_year': 2026, 'title': 'Grade 4 CBC - Term 2 Master Homeschool Box', 'subtitle': 'KICD Syllabi Aligned: Decimals, Digestive Health, Kenyan Geography, Creative Arts', 'price_kes': 6500.0, 'badge': 'Official KICD Standard', 'features': ['12 Complete Term 2 Weekly Modules', 'Decimals & Measurement Practicals', 'Human Body Systems & Nutrition Labs']},
        'defaults': [{'name': 'Mathematics', 'time': '08:30 AM - 09:15 AM', 'materials': ['Ruler', 'Decimal grid'], 'is_lab': False, 'photo': False}, {'name': 'Science & Tech', 'time': '09:30 AM - 10:15 AM', 'materials': ['Digestive system model chart', 'Magnifier'], 'is_lab': True, 'photo': True}, {'name': 'English & Kiswahili', 'time': '10:30 AM - 11:15 AM', 'materials': ['Exercise book', 'Dictionary'], 'is_lab': False, 'photo': False}],
        'pdf_schedule': [['Day', 'Subject Area', 'Term 2 Focus', 'Materials Needed'], ['Mon', 'Mathematics', 'Decimals & Fraction Conversions', 'Decimal grid, Ruler'], ['Tue', 'Science & Tech', 'Human Digestive System Model', 'Chart, Playdough'], ['Wed', 'English', 'Narrative Writing: Trip to Lake Nakuru', 'Lined notebook, Pen'], ['Thu', 'Kiswahili', 'Kusoma na Kuandika: Ushairi', 'Daftari ya Ushairi'], ['Fri', 'Agriculture', 'Weeding & Moisture Retention Labs', 'Garden hoe, Mulch']]
    },

    # 2. CBC Grade 4 Term 3
    {
        'json_name': 'kicd_grade4_cbc_term3.json',
        'pdf_name': 'Grade4_CBC_Term3_Printable_Pack.pdf',
        'curriculum': {'code': 'CBC', 'name': 'Kenya Competency-Based Curriculum (CBC)', 'tagline': 'KICD Aligned', 'description': 'National curriculum approved by KICD.'},
        'term_package': {'grade_level': 'Grade 4', 'term': 3, 'academic_year': 2026, 'title': 'Grade 4 CBC - Term 3 Master Homeschool Box', 'subtitle': 'KICD Syllabi Aligned: End-of-Year Consolidation, CBA Assessment Portfolio, Algebra Basics', 'price_kes': 6500.0, 'badge': 'KNEC CBA Annual Portfolio', 'features': ['12 Complete Term 3 Weekly Modules', 'KNEC Level 1-4 End of Year CBA Evaluation', 'Comprehensive Annual Portfolio Wrap-up']},
        'defaults': [{'name': 'Mathematics', 'time': '08:30 AM - 09:15 AM', 'materials': ['Math workbook', 'Compass'], 'is_lab': False, 'photo': False}, {'name': 'Science & Tech', 'time': '09:30 AM - 10:15 AM', 'materials': ['Electric circuit items (battery, bulb, wire)'], 'is_lab': True, 'photo': True}, {'name': 'Social Studies & CSL', 'time': '10:30 AM - 11:15 AM', 'materials': ['Community service log', 'Atlas'], 'is_lab': False, 'photo': True}],
        'pdf_schedule': [['Day', 'Subject Area', 'Term 3 Focus', 'Materials Needed'], ['Mon', 'Mathematics', '2D/3D Geometry & Area Calculations', 'Grid paper, Geometry set'], ['Tue', 'Science & Tech', 'Simple Electric Circuits Practical', '1.5V AA battery, Torch bulb, Copper wire'], ['Wed', 'Social Studies', 'National Symbols & Heritage of Kenya', 'Atlas, Kenya Flag diagram'], ['Thu', 'Creative Arts', 'Kitenge Fabric Mosaic Art Portfolio', 'Scrap fabric, Glue, Cardboard'], ['Fri', 'Community Service', 'Environmental Clean-up & Tree Planting', 'Seedling, Garden gloves']]
    },

    # 3. Cambridge Stage 4 Primary Term 2
    {
        'json_name': 'cambridge_stage4_primary_term2.json',
        'pdf_name': 'Cambridge_Stage4_Primary_Term2_Printable_Pack.pdf',
        'curriculum': {'code': 'CAMBRIDGE', 'name': 'Cambridge International Primary (UK)', 'tagline': 'CAIE Aligned', 'description': 'British International CAIE framework.'},
        'term_package': {'grade_level': 'Stage 4 (Primary)', 'term': 2, 'academic_year': 2026, 'title': 'Stage 4 Cambridge Primary - Term 2 Master Box', 'subtitle': 'CAIE Aligned: Fractions & Decimals, States of Matter, Non-Fiction Information Reports', 'price_kes': 8500.0, 'badge': 'Cambridge CAIE Gold Standard', 'features': ['12 Weeks CAIE Stage 4 Term 2 Guides', 'States of Matter & Solid-Liquid Transitions', 'Informational Text Analysis & Writing']},
        'defaults': [{'name': 'Cambridge Mathematics', 'time': '08:30 AM - 09:15 AM', 'materials': ['Fractions chart', 'Calculator'], 'is_lab': False, 'photo': False}, {'name': 'Cambridge Science', 'time': '09:30 AM - 10:15 AM', 'materials': ['Ice cubes', 'Thermometer', 'Beaker'], 'is_lab': True, 'photo': True}, {'name': 'Cambridge English', 'time': '10:30 AM - 11:15 AM', 'materials': ['Non-fiction reader', 'Highlighters'], 'is_lab': False, 'photo': False}],
        'pdf_schedule': [['Day', 'Subject Area', 'Cambridge Stage 4 Term 2 Focus', 'Everyday Materials'], ['Mon', 'Cambridge Math', 'Equivalent Fractions & Mixed Numbers', 'Fraction wall printable, Ruler'], ['Tue', 'Cambridge Science', 'States of Matter: Melting & Boiling Points', 'Thermometer, Ice, Warm water'], ['Wed', 'Cambridge English', 'Informational Texts: Formal Letter Writing', 'Lined paper, Envelope'], ['Thu', 'Global Perspectives', 'Renewable Energy Comparison in Africa', 'Solar lamp, Factsheet'], ['Fri', 'Computing', 'Debugging Scratch Conditional Statements', 'Computer / Scratch 3.0']]
    },

    # 4. Cambridge Stage 4 Primary Term 3
    {
        'json_name': 'cambridge_stage4_primary_term3.json',
        'pdf_name': 'Cambridge_Stage4_Primary_Term3_Printable_Pack.pdf',
        'curriculum': {'code': 'CAMBRIDGE', 'name': 'Cambridge International Primary (UK)', 'tagline': 'CAIE Aligned', 'description': 'British International CAIE framework.'},
        'term_package': {'grade_level': 'Stage 4 (Primary)', 'term': 3, 'academic_year': 2026, 'title': 'Stage 4 Cambridge Primary - Term 3 Master Box', 'subtitle': 'CAIE Aligned: Cambridge Progression Test Preparation, Light & Sound Waves, Poetry Analysis', 'price_kes': 8500.0, 'badge': 'Cambridge Progression Test Ready', 'features': ['12 Weeks Cambridge Progression Test Prep', 'Light Refraction & Sound Waves Experiments', 'Poetic Forms & Extended Comprehension']},
        'defaults': [{'name': 'Cambridge Mathematics', 'time': '08:30 AM - 09:15 AM', 'materials': ['Progression test papers', 'Protractor'], 'is_lab': False, 'photo': False}, {'name': 'Cambridge Science', 'time': '09:30 AM - 10:15 AM', 'materials': ['Flashlight', 'Glass prism / mirror'], 'is_lab': True, 'photo': True}, {'name': 'Cambridge English', 'time': '10:30 AM - 11:15 AM', 'materials': ['Poetry anthology', 'Dictionary'], 'is_lab': False, 'photo': False}],
        'pdf_schedule': [['Day', 'Subject Area', 'Cambridge Stage 4 Term 3 Focus', 'Everyday Materials'], ['Mon', 'Cambridge Math', 'Angles & Symmetry in 2D Polygons', 'Protractor, Grid paper'], ['Tue', 'Cambridge Science', 'Light Reflection & Refraction in Water', 'Glass of water, Torch, Mirror'], ['Wed', 'Cambridge English', 'Poetry Imagery: Metaphors & Personification', 'Poetry sheet, Colored pens'], ['Thu', 'Progression Test Prep', 'Stage 4 Primary Checkpoint Mock Review', 'Sample exam paper, Timer'], ['Fri', 'Digital Literacy', 'Creating Multi-Slide Multimedia Presentation', 'Laptop / Tablet']]
    },

    # 5. Cambridge IGCSE High School (Year 10 / Stage 10)
    {
        'json_name': 'cambridge_igcse_year10_term1.json',
        'pdf_name': 'Cambridge_IGCSE_Year10_Term1_Printable_Pack.pdf',
        'curriculum': {'code': 'CAMBRIDGE', 'name': 'Cambridge International Primary (UK)', 'tagline': 'CAIE Aligned', 'description': 'British International CAIE framework.'},
        'term_package': {'grade_level': 'IGCSE Year 10 (High School)', 'term': 1, 'academic_year': 2026, 'title': 'Cambridge IGCSE Year 10 - Term 1 Master Box', 'subtitle': 'CAIE IGCSE Aligned: Mathematics (0580), Physics (0625), Biology (0610), First Language English (0500), Business (0450)', 'price_kes': 12000.0, 'badge': 'Cambridge IGCSE Gold Standard', 'features': ['12 High-Yield IGCSE Syllabus Modules', 'Past Paper Question Breakdown & Mark Schemes', 'Physics & Chemistry Household Micro-Labs', 'Paper 1 & Paper 2 Exam Technique Workshops']},
        'defaults': [{'name': 'IGCSE Mathematics (0580)', 'time': '08:30 AM - 09:30 AM', 'materials': ['Scientific calculator', 'Past paper booklet'], 'is_lab': False, 'photo': False}, {'name': 'IGCSE Sciences (Physics 0625 / Bio 0610)', 'time': '09:45 AM - 10:45 AM', 'materials': ['Microscope / Lens', 'Chemical tests kit'], 'is_lab': True, 'photo': True}, {'name': 'IGCSE English & Business (0500/0450)', 'time': '11:00 AM - 12:00 PM', 'materials': ['Case study booklet', 'Highlighters'], 'is_lab': False, 'photo': False}],
        'pdf_schedule': [['Day', 'Subject Area', 'IGCSE Year 10 Core Focus', 'Required Material'], ['Mon', 'IGCSE Math (0580)', 'Algebraic Indices, Surds & Quadratic Factorization', 'Casio FX-991EX calculator, Past Paper 2'], ['Tue', 'IGCSE Physics (0625)', 'Kinematics: Velocity-Time Graphs & Acceleration', 'Graph paper, Stopwatch, Toy car ramp'], ['Wed', 'IGCSE Biology (0610)', 'Enzyme Activity vs Temperature & pH Investigation', 'Hydrogen peroxide / potato catalase, Yeast'], ['Thu', 'IGCSE English (0500)', 'Directed Writing: 25-Mark Speech & Article Critique', 'Article insert, Highlighters'], ['Fri', 'IGCSE Business (0450)', 'Market Segmentation, Product Life Cycle & Break-Even', 'Case study extract, Financial calculator']]
    },

    # 6. US High School Diploma & GED Prep (Grades 9-12)
    {
        'json_name': 'us_high_school_ged_term1.json',
        'pdf_name': 'US_High_School_GED_Term1_Printable_Pack.pdf',
        'curriculum': {'code': 'US_COMMON_CORE', 'name': 'US Common Core & Next Gen Science (American K-12)', 'tagline': 'US Standards', 'description': 'American K-12 standards.'},
        'term_package': {'grade_level': 'High School / GED (Grades 9-12)', 'term': 1, 'academic_year': 2026, 'title': 'US High School Diploma & GED Prep - Term 1 Box', 'subtitle': 'American High School Credits: Algebra II, US Government, AP Biology Inquiry, Literature & Composition', 'price_kes': 11000.0, 'badge': 'US High School Diploma & GED', 'features': ['12 Accredited High School Credit Modules', 'GED Math & Science Practice Sequences', 'US Constitution & Federal Government Inquiry', 'College Essay & Critical Argumentation']},
        'defaults': [{'name': 'Algebra II & Pre-Calculus', 'time': '08:30 AM - 09:30 AM', 'materials': ['Graphing calculator', 'Formulas chart'], 'is_lab': False, 'photo': False}, {'name': 'AP Biology & STEM Lab', 'time': '09:45 AM - 10:45 AM', 'materials': ['Spectrophotometer simulator / home reagents'], 'is_lab': True, 'photo': True}, {'name': 'US History & English Lit', 'time': '11:00 AM - 12:00 PM', 'materials': ['Federalist Papers extract', 'Notebook'], 'is_lab': False, 'photo': False}],
        'pdf_schedule': [['Day', 'Subject Area', 'High School / GED Focus', 'Everyday Materials'], ['Mon', 'Algebra II', 'Polynomial Functions & Complex Numbers', 'Graphing calculator (TI-84 / Desmos)'], ['Tue', 'AP Biology', 'Cellular Respiration & ATP Synthesis Kinetics', 'Yeast, Sugar, Balloons, Water bath'], ['Wed', 'English Literature', 'Rhetorical Analysis: American Speeches (Civil Rights)', 'Speech text transcripts, Highlighters'], ['Thu', 'US Government', 'Separation of Powers & Constitutional Case Law', 'US Constitution booklet'], ['Fri', 'GED Math / SAT Prep', 'Timed Standardized Practice Test & Strategy', 'Standardized answer sheet, Timer']]
    },

    # 7. CBC Grade 10 Senior Secondary (STEM & Arts)
    {
        'json_name': 'kicd_grade10_senior_cbc_term1.json',
        'pdf_name': 'Grade10_Senior_CBC_Term1_Printable_Pack.pdf',
        'curriculum': {'code': 'CBC', 'name': 'Kenya Competency-Based Curriculum (CBC)', 'tagline': 'KICD Aligned', 'description': 'National curriculum approved by KICD.'},
        'term_package': {'grade_level': 'Grade 10 (Senior Secondary)', 'term': 1, 'academic_year': 2026, 'title': 'Grade 10 Senior CBC - Term 1 STEM & Arts Box', 'subtitle': 'KICD Senior School Pathways: Pure Sciences (Physics/Chemistry/Bio), Advanced Math, Humanities', 'price_kes': 9500.0, 'badge': 'KICD Senior School Pathway', 'features': ['12 Advanced Senior School Inquiry Modules', 'Specialized STEM Pathway Practicals', 'KNEC CBA Senior School Assessment Framework']},
        'defaults': [{'name': 'Advanced Mathematics', 'time': '08:30 AM - 09:30 AM', 'materials': ['Scientific calculator', 'Geometry set'], 'is_lab': False, 'photo': False}, {'name': 'Pure Sciences (Physics/Chem)', 'time': '09:45 AM - 10:45 AM', 'materials': ['Titration / Mechanics kit', 'Lab coat'], 'is_lab': True, 'photo': True}, {'name': 'Humanities & Applied Tech', 'time': '11:00 AM - 12:00 PM', 'materials': ['Atlas', 'Coding editor'], 'is_lab': False, 'photo': False}],
        'pdf_schedule': [['Day', 'Subject Area', 'Grade 10 Senior Focus', 'Materials Needed'], ['Mon', 'Advanced Math', 'Trigonometric Functions & Vectors in 2D', 'Scientific calculator, Graph book'], ['Tue', 'Chemistry', 'Molar Solutions & Acid-Base Titration', 'Vinegar, Baking soda indicator, Dropper'], ['Wed', 'Physics', 'Circular Motion & Centripetal Acceleration', 'String, Rubber stopper, Glass tube'], ['Thu', 'Biology', 'Genetic Inheritance & Punnett Squares', 'Genetics chart, Colored beads'], ['Fri', 'Pre-Career Workshop', 'Python Programming & Hardware Automation', 'Laptop, Micro:bit / Arduino simulator']]
    }
]

# Run generation and ingestion loop
for cfg in multi_term_configs:
    t_num = cfg['term_package'].get('term', 1)
    weeks = make_weeks_for_term(t_num, cfg['term_package']['grade_level'], cfg['defaults'])
    pkg_full_data = {
        'curriculum': cfg['curriculum'],
        'term_package': cfg['term_package'],
        'weeks': weeks
    }
    
    t_path = os.path.join(TEMPLATES_DIR, cfg['json_name'])
    with open(t_path, 'w') as f:
        json.dump(pkg_full_data, f, indent=2)
        
    d_path = os.path.join(DOWNLOADS_DIR, cfg['json_name'])
    with open(d_path, 'w') as f:
        json.dump(pkg_full_data, f, indent=2)
        
    print(f'  ✓ [JSON Saved] {cfg["json_name"]}')
    
    ingest_package(pkg_full_data)
    
    generate_pdf_pack(
        cfg['curriculum']['name'],
        cfg['term_package']['subtitle'],
        cfg['term_package']['grade_level'],
        cfg['curriculum']['code'],
        cfg['pdf_schedule'],
        [
            {'title': f'WORKSHEET #1: {cfg["defaults"][0]["name"].upper()}', 'script': f'Guide your high school / term learner through advanced problem-solving in {cfg["defaults"][0]["name"]}.', 'activity': '1. Guided theory.\n2. Stepped derivation.\n3. Independent problem set.', 'materials': ', '.join(cfg['defaults'][0]['materials'])},
            {'title': f'PRACTICAL LAB: {cfg["defaults"][1]["name"].upper()}', 'script': f'Perform the hands-on lab investigation and record observational empirical metrics.', 'activity': '1. Setup apparatus.\n2. Record variables.\n3. Plot data graph and evaluate margin of error.', 'materials': ', '.join(cfg['defaults'][1]['materials'])}
        ],
        cfg['pdf_name']
    )

print("=== ALL TERMS 2 & 3 AND HIGH SCHOOL STREAMS SEEDED SUCCESSFULLY! ===")
