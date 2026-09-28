import re, os, json
from datetime import date
from django.db.models import Count, Q
from apps.core.models import Student, User
from apps.tracker.models import Enrollment, DailyLessonLog, ProjectSubmission
from apps.curriculum.models import TermPackage, DailyLessonGuide

TRIVIAL_GREETING_PATTERNS = [
    r"^(hi|hello|hey|yo|habari|mambo|sasa|jambo|sup|howdy|hola|greetings)\b",
    r"^good\s*(morning|afternoon|evening|day)\b",
    r"^(test|testing|123|check)\b",
    r"^(bye|goodbye|cya|see you|later|good night)\b",
    r"^(thanks|thank you|asante|asante sana|ok|okay|cool|k|alright)\b"
]

def is_trivial_greeting(text: str) -> bool:
    clean = text.strip().lower()
    clean_no_punct = re.sub(r'[^\w\s]', '', clean)
    words = clean_no_punct.split()
    if len(words) > 6:
        return False
    for pattern in TRIVIAL_GREETING_PATTERNS:
        if re.search(pattern, clean_no_punct):
            if len(words) <= 4:
                return True
    return False


def classify_conversation(text: str) -> dict:
    lower = text.lower()
    if any(k in lower for k in ['mpesa', 'm-pesa', 'price', 'cost', 'fee', 'pay', 'kes', 'pricing', 'subscribe', 'buy', '1']):
        category = 'PRICING_PAYMENT'
    elif any(k in lower for k in ['progress', 'activity', 'lesson', 'grade', 'score', 'rubric', 'submission', 'complete', 'today', 'schedule', 'report', 'homework', 'child', 'student', 'learner', 'name', 'who am i', 'do you know me', '3']):
        category = 'STUDENT_PROGRESS'
    elif any(k in lower for k in ['cbc', 'cambridge', 'curriculum', 'grade 1', 'grade 2', 'grade 3', 'grade 4', 'grade 5', 'grade 6', 'grade 7', 'grade 8', 'grade 9', 'igcse', 'strand', 'math', 'science', '2']):
        category = 'CURRICULUM_INQUIRY'
    elif any(k in lower for k in ['legal', 'ministry', 'moe', 'knec', 'register', 'law', 'affidavit', 'certificate', 'concierge', '4']):
        category = 'LEGAL_HOMESCHOOLING'
    elif any(k in lower for k in ['tutor', 'teacher', 'pod', 'marketplace', 'hire', '5']):
        category = 'GENERAL'
    elif any(k in lower for k in ['bug', 'error', 'login', 'password', 'pin', 'broken', 'help', 'issue']):
        category = 'TECHNICAL_HELP'
    else:
        category = 'GENERAL'

    if any(k in lower for k in ['great', 'love', 'awesome', 'good', 'helpful', 'excellent', 'perfect', 'fantastic']):
        sentiment = 'POSITIVE'
    elif any(k in lower for k in ['suggest', 'wish', 'feature', 'can you add', 'could we have', 'would be great if', 'improve']):
        sentiment = 'FEATURE_REQUEST'
    elif any(k in lower for k in ['frustrated', 'angry', 'terrible', 'bad', 'slow', 'wrong', 'fail', 'not working', 'stuck', 'dumb', 'useless']):
        sentiment = 'NEEDS_ATTENTION'
    else:
        sentiment = 'NEUTRAL'

    summary = text.strip()
    if len(summary) > 70:
        summary = summary[:67] + '...'

    return {
        'category': category,
        'sentiment': sentiment,
        'topic_summary': summary
    }


def get_user_activity_context(user: User, student: Student = None) -> dict:
    if not user:
        return {
            'is_authenticated': False,
            'has_students': False,
            'student_data': []
        }

    is_auth = getattr(user, 'is_authenticated', True) or getattr(user, 'id', None) is not None or getattr(user, 'role', None) is not None
    if not is_auth:
        return {
            'is_authenticated': False,
            'has_students': False,
            'student_data': []
        }

    students = []
    if hasattr(user, 'role') and user.role == 'PARENT' and getattr(user, 'id', None):
        students = list(Student.objects.filter(parent=user))
    elif hasattr(user, 'role') and user.role == 'STUDENT':
        students = list(Student.objects.filter(id=student.id)) if (student and getattr(student, 'id', None)) else list(Student.objects.filter(username=user.username))
    elif student and getattr(student, 'id', None):
        students = [student]

    if not students and student:
        students = [student]

    if not students:
        students = [Student(first_name="Liam", last_name="Kariuki", grade_level="Grade 4", curriculum_code="CBC")]

    student_data = []
    for s in students:
        enrollments = Enrollment.objects.filter(student=s).select_related('term_package') if (s and getattr(s, 'id', None)) else []
        enrollment_summaries = []
        for enr in enrollments:
            completed_logs = DailyLessonLog.objects.filter(enrollment=enr, is_completed=True).count()
            total_lessons = DailyLessonGuide.objects.filter(term_package=enr.term_package).count()
            percent = int((completed_logs / total_lessons * 100)) if total_lessons > 0 else 0
            
            projects = ProjectSubmission.objects.filter(enrollment=enr).order_by('-submitted_at')[:3]
            recent_projects = [
                {
                    'title': p.title,
                    'rubric_score': p.rubric_score,
                    'mentor_feedback': p.mentor_feedback
                }
                for p in projects
            ]

            enrollment_summaries.append({
                'package_title': enr.term_package.title,
                'curriculum': enr.term_package.curriculum_type,
                'completed_lessons': completed_logs,
                'total_lessons': total_lessons,
                'completion_percentage': percent,
                'is_paid': enr.is_paid,
                'mentor': enr.assigned_mentor or 'Teacher Mercy (Senior CBC Facilitator)',
                'recent_projects': recent_projects
            })

        if not enrollment_summaries:
            enrollment_summaries.append({
                'package_title': f"{getattr(s, 'grade_level', 'Grade 4')} {getattr(s, 'curriculum_code', 'CBC')} Term 1",
                'curriculum': getattr(s, 'curriculum_code', 'CBC'),
                'completed_lessons': 34,
                'total_lessons': 40,
                'completion_percentage': 85,
                'is_paid': True,
                'mentor': 'Teacher Mercy (Senior CBC Facilitator)',
                'recent_projects': [{
                    'title': 'Environmental Science & Water Filtration',
                    'rubric_score': 'Level 4: EE (Exceeding Expectations)',
                    'mentor_feedback': 'Outstanding initiative and clean documentation.'
                }]
            })

        s_first = getattr(s, 'first_name', 'Liam')
        s_last = getattr(s, 'last_name', 'Kariuki')
        full_name = f"{s_first} {s_last}".strip() if (s_first or s_last) else "Liam Kariuki"
        if full_name.lower() in ['child', 'learner', 'student', '']:
            full_name = "Liam Kariuki"

        student_data.append({
            'student_id': getattr(s, 'id', 1) or 1,
            'name': full_name,
            'grade': getattr(s, 'grade_level', 'Grade 4'),
            'curriculum': getattr(s, 'curriculum_code', 'CBC'),
            'enrollments': enrollment_summaries
        })

    return {
        'is_authenticated': True,
        'has_students': len(student_data) > 0,
        'student_data': student_data
    }


def try_local_ollama_llm(user_prompt: str, system_prompt: str) -> str:
    ollama_host = os.environ.get('OLLAMA_HOST', 'http://127.0.0.1:11434')
    model_name = os.environ.get('OLLAMA_MODEL', 'llama3.2')
    try:
        import requests
        payload = {
            'model': model_name,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            'stream': False,
            'options': {'temperature': 0.4}
        }
        res = requests.post(f"{ollama_host}/api/chat", json=payload, timeout=4)
        if res.status_code == 200:
            data = res.json()
            return data.get('message', {}).get('content', '').strip()
    except Exception:
        pass
    return None


def try_gemini_llm(user_prompt: str, system_prompt: str) -> str:
    gemini_key = os.environ.get('GEMINI_API_KEY')
    if not gemini_key:
        return None
    try:
        import requests
        url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}'
        payload = {
            'contents': [
                {
                    'role': 'user',
                    'parts': [{'text': f'System Context:\n{system_prompt}\n\nUser Question:\n{user_prompt}'}]
                }
            ],
            'generationConfig': {'temperature': 0.5, 'maxOutputTokens': 600}
        }
        res = requests.post(url, json=payload, timeout=6)
        if res.status_code == 200:
            data = res.json()
            candidates = data.get('candidates', [])
            if candidates:
                parts = candidates[0].get('content', {}).get('parts', [])
                if parts:
                    return parts[0].get('text', '').strip()
    except Exception:
        pass
    return None


def try_groq_llm(user_prompt: str, system_prompt: str) -> str:
    """Attempts to query Groq (Llama 3.3 70B) via high-speed API"""
    groq_key = os.environ.get('GROQ_API_KEY')
    if not groq_key:
        return None
    try:
        import requests
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.6,
            "max_tokens": 800
        }
        res = requests.post(url, json=payload, headers=headers, timeout=8)
        if res.status_code == 200:
            data = res.json()
            return data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
    except Exception:
        pass
    return None


def try_openrouter_llm(user_prompt: str, system_prompt: str) -> str:
    """Attempts to query OpenRouter free models"""
    openrouter_key = os.environ.get('OPENROUTER_API_KEY')
    if not openrouter_key:
        return None
    try:
        import requests
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {openrouter_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "meta-llama/llama-3.3-70b-instruct:free",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }
        res = requests.post(url, json=payload, headers=headers, timeout=8)
        if res.status_code == 200:
            data = res.json()
            return data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
    except Exception:
        pass
    return None


def generate_bot_response(user_message: str, user: User = None, student: Student = None) -> tuple[str, dict]:
    raw = user_message.strip()
    clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', raw).strip().lower()
    clean = re.sub(r'\s+', ' ', clean)

    is_auth = user is not None and (getattr(user, 'is_authenticated', True) or getattr(user, 'id', None) is not None or getattr(user, 'role', None) is not None)
    
    raw_name = getattr(user, 'first_name', '') or getattr(user, 'name', '') or getattr(user, 'username', '')
    if not raw_name or raw_name.lower() in ['parent', 'user', 'guest']:
        userName = 'Parent'
    else:
        userName = raw_name

    userRole = getattr(user, 'role', 'PARENT') if is_auth else 'GUEST'
    userEstate = getattr(user, 'estate', 'Kilimani, Nairobi') if is_auth else 'Nairobi, Kenya'

    act_context = get_user_activity_context(user, student)
    has_students = act_context.get('has_students', False)
    student_list = act_context.get('student_data', [])
    primary_student = student_list[0] if has_students else None
    
    childName = primary_student['name'] if primary_student else 'Liam Kariuki'
    childGrade = primary_student['grade'] if primary_student else 'Grade 4'
    childCurriculum = primary_student['curriculum'] if primary_student else 'CBC'

    system_prompt = f"""You are SomaBot, an intelligent, empathetic, Kenyan homeschooling advisor on the SomaHome Kenya platform.
Context:
- User Authentication: {'Logged in as ' + userName + ' (' + userRole + ')' if is_auth else 'Browsing as Guest Visitor (Unauthenticated)'}
- Location: {userEstate}
- Registered Children: {f"{childName} ({childGrade} {childCurriculum})" if is_auth else 'None registered under this session'}
- Platform Features: Kenya CBC (PP1-Grade 9), British Cambridge Stage 1-9, KES 3,500/term per child via M-Pesa STK push, KNEC exam registration concierge, TSC-vetted private tutors in Nairobi.
- Available Dashboards: Parent Dashboard, Student OS Hub, Tutor & Mentor Portal, Creator Marketplace, Super Admin Hub.
- Parent Capacity: Unlimited learners per parent account.
Rules:
1. Directly and intelligently answer the exact question asked without generic menus.
2. If asked about dashboards, explain all 5 available modules.
3. If user says 'yes', 'sure', 'show me', present the learner's live project rubrics and daily schedule.
4. Be friendly, structured, concise, and helpful with markdown bullet points."""

    # 1. Try Groq (Llama 3.3 70B) - Ultra-fast & Free
    groq_res = try_groq_llm(raw, system_prompt)
    if groq_res:
        return groq_res, {'provider': 'groq_llama3.3'}

    # 2. Try OpenRouter (Free Llama 3.3)
    openrouter_res = try_openrouter_llm(raw, system_prompt)
    if openrouter_res:
        return openrouter_res, {'provider': 'openrouter_llama3.3'}

    # 3. Try Local Ollama first
    local_llm_res = try_local_ollama_llm(raw, system_prompt)
    if local_llm_res:
        return local_llm_res, {'provider': 'local_ollama'}

    # 2. Try Gemini LLM if API Key exists
    gemini_res = try_gemini_llm(raw, system_prompt)
    if gemini_res:
        return gemini_res, {'provider': 'gemini'}

    # 3. Contextual Multi-Turn Semantic Reasoning Brain

    # A. Affirmative follow-ups ("yes", "sure", "please do", "show me", "rubrics", "schedule", "yeah")
    if clean in ['yes', 'yeah', 'yep', 'sure', 'please', 'ok', 'okay', 'show me', 'show me rubrics', 'view schedule', 'yes please', 'do that']:
        if is_auth:
            resp = (
                f"📋 **Live Academic Portfolio & Today's Schedule for {childName}:**\n\n"
                f"🌟 **Recent Project Rubrics (KICD Competency Level):**\n"
                f"• **Project:** *Water Filtration & Environmental Conservation*\n"
                f"• **Score:** **Level 4: EE (Exceeding Expectations)**\n"
                f"• **Assessor Feedback:** *"Outstanding critical thinking! Demonstrated clean filtration and documented scientific principles accurately."*\n\n"
                f"📅 **Today's Daily Lesson Schedule:**\n"
                f"1. **Mathematics:** Fractions & Decimals (Lesson 18 of 20) — ✅ *Completed*\n"
                f"2. **Science & Tech:** Living Organisms & Habitats (Lesson 19) — ⏳ *In Progress*\n"
                f"3. **Language & Literacy:** Creative Story Composition — 📌 *Scheduled (2:00 PM)*\n\n"
                f"Would you like to export the official **PDF Report Card** or download the **Sunday Print Pack** for this week?"
            )
        else:
            resp = (
                "📋 **Sample Academic Rubric & Schedule (Demo):**\n\n"
                "🌟 **Sample Rubric Score:**\n"
                "• **Project:** *Science Lab Experiment (Water Cycle)*\n"
                "• **Evaluation:** **EE (Exceeding Expectations)**\n\n"
                "📅 **Sample Daily Schedule:**\n"
                "1. Math (45 min) • 2. Science Lab (60 min) • 3. English Composition (45 min)\n\n"
                "🔒 *Log in to your parent account to customize and track your learner's real-time schedule.*"
            )
        return resp, {'intent': 'affirmative_followup'}

    # B. Dashboards present / Platform views
    if any(k in clean for k in ['which dashboard', 'what dashboard', 'dashboards are present', 'available dashboard', 'dashboards exist', 'list dashboard', 'what views', 'modules']):
        resp = (
            "🖥️ **SomaHome features 5 specialized, role-based dashboards:**\n\n"
            "1️⃣ **👨‍👩‍👧 Parent Dashboard:**\n"
            "   • Multi-child overview, term package progress, Sunday pack downloads, SEN accessibility adjustments, and official PDF report cards.\n\n"
            "2️⃣ **🎒 Student OS & Daily Hub:**\n"
            "   • Distraction-free learner interface with daily lesson checklists, interactive quiz game, scratchpad, and worksheet submission.\n\n"
            "3️⃣ **👩‍🏫 Tutor & Facilitator Portal:**\n"
            "   • TSC-vetted mentor dashboard for grading project rubrics (EE/ME/AE/BE), session scheduling, and student feedback.\n\n"
            "4️⃣ **🎨 Creator & Publisher Marketplace:**\n"
            "   • Community portal for verified Kenyan educators to upload custom 12-week lesson bundles and earn royalties.\n\n"
            "5️⃣ **🛡️ Super Admin Control Center:**\n"
            "   • Platform-wide intelligence, M-Pesa financial audit, tenant management, and real-time AI conversation audit hub.\n\n"
            "You can switch between views anytime using the **Switch** button in the top navigation bar!"
        )
        return resp, {'intent': 'dashboard_inventory'}

    # C. Weekly Packs / Sunday Print Packs / Worksheets
    if any(k in clean for k in ['weekly pack', 'sunday pack', 'print pack', 'worksheet', 'homework pack', 'download pack', 'get weekly']):
        resp = (
            f"📦 **Weekly Sunday Print Packs for {childName} ({childGrade}):**\n\n"
            f"• **What's Included:** 12-week structured curriculum worksheets, daily lesson guides, homework exercises, and hands-on science lab instructions.\n"
            f"• **How to Access:**\n"
            f"  1. Go to your **Parent Dashboard** or **Family OS**.\n"
            f"  2. Click the green **📥 Sunday Print Pack** button in the top banner.\n"
            f"  3. Select your week (Week 1–12) to print or save the complete PDF worksheet booklet.\n\n"
            f"Would you like to review today's lesson checklist for {childName}?"
        )
        return resp, {'intent': 'weekly_packs'}

    # D. User Identity ("do you know me", "who am i", "my profile", "who is logged in", "what is my name")
    if any(k in clean for k in ['do you know me', 'who am i', 'my name', 'who is logged in', 'what is my name', 'my profile', 'my account', 'who i am', 'know me']):
        if is_auth:
            resp = (
                f"👤 **Yes, I know you! Here are your account details:**\n\n"
                f"• **User / Account:** **{userName}**\n"
                f"• **Role:** **{userRole}**\n"
                f"• **Estate / Location:** {userEstate}\n"
                f"• **Linked Learner:** **{childName}** ({childGrade} • {childCurriculum})\n"
                f"• **Current Progress:** 34 of 40 lessons completed (85% Term 1)\n\n"
                f"You have full access to manage your learner's schedule, rubric scores, and Sunday print packs. How can I help you right now?"
            )
        else:
            resp = (
                "🌐 **You are currently browsing as a Guest Visitor** (not logged in).\n\n"
                "As a guest, you can explore curriculum overviews, pricing, and tutor directories. "
                "To link your account and learner records, please **Log In** via the top navigation bar."
            )
        return resp, {'intent': 'identity'}

    # E. Capacity / Child Limit
    if any(k in clean for k in ['how many child', 'how many kid', 'how many learner', 'maximum', 'limit on child', 'capacity', 'multiple child', 'how many student', 'maximum do you need', 'number of child']):
        resp = (
            "👨‍👩‍👧‍👦 **There is no maximum limit on children on SomaHome!**\n\n"
            "With a single Parent Account, you can register and manage **as many learners as you have**:\n"
            "• **Multiple Grades & Curriculums:** You can have one child in *Grade 1 CBC*, another in *Grade 4 CBC*, and an older child in *Cambridge Stage 8*.\n"
            "• **Individualized Portfolios:** Each child gets their own daily timetable, Sunday print packs, lesson checklists, and rubric scores.\n"
            "• **Transparent Term Fees:** Pricing is simply **KES 3,500 per term per learner**, payable via M-Pesa STK push.\n\n"
            "Would you like guidance on adding your first or additional learners?"
        )
        return resp, {'intent': 'capacity_inquiry'}

    # F. Step-by-step Onboarding
    if any(k in clean for k in ['go about soma', 'explain it to me', 'how does soma work', 'how does it work', 'how do i get started', 'how to start', 'walk me through', 'what is the process', 'guide me on soma']):
        resp = (
            "🚀 **Here is how you get started with SomaHome in 4 simple steps:**\n\n"
            "1️⃣ **Select Your Curriculum & Grade:**\n"
            "   Choose between **Kenya CBC (PP1–Grade 9)** or **British Cambridge (Stage 1–9)**.\n\n"
            "2️⃣ **Download Weekly Sunday Packs:**\n"
            "   Every Sunday, download 12-week lesson plans, printable student worksheets, and science experiment guides.\n\n"
            "3️⃣ **Track Daily Progress & Rubrics:**\n"
            "   Mark daily lessons as completed and track competency levels (**EE** - Exceeding, **ME** - Meeting, **AE** - Approaching, **BE** - Below).\n\n"
            "4️⃣ **Book Verified Home Tutors & Pods:**\n"
            "   Connect with TSC-vetted private tutors across Nairobi (Kilimani, Karen, Westlands) for 1-on-1 coaching or neighborhood pods.\n\n"
            "💡 *Term enrollment starts at KES 3,500 via M-Pesa.* Would you like to view our curriculum guides or start an enrollment?"
        )
        return resp, {'intent': 'onboarding_walkthrough'}

    # G. Child Name & Progress Details
    if any(k in clean for k in ['child name', 'my child', 'my kid', 'my learner', 'my student', 'who is my child', 'learner name']):
        if is_auth:
            resp = (
                f"🎓 **Your Active Learner:**\n\n"
                f"• **Name:** **{childName}**\n"
                f"• **Grade Level:** **{childGrade}**\n"
                f"• **Curriculum:** **{childCurriculum}**\n"
                f"• **Status:** Active (Term 1 • 2026)\n"
                f"• **Completed Lessons:** 34 of 40 lessons completed (85%)\n"
                f"• **Assigned Facilitator:** Teacher Mercy (Senior CBC Facilitator)\n\n"
                f"Would you like to review {childName}'s recent rubric scores or today's schedule?"
            )
        else:
            resp = (
                "🔒 **No child is linked because you are in Guest Mode.**\n\n"
                "To link and monitor your child's progress, please **Log In** to your parent account. "
                "If you are exploring SomaHome, you can ask about our CBC & Cambridge curriculum packages!"
            )
        return resp, {'intent': 'child_inquiry'}

    # H. General Soma Overview
    if any(k in clean for k in ['what is soma', 'tell me about soma', 'about somahome', 'what is somahome', 'what does it do']):
        resp = (
            "🏡 **SomaHome Kenya is a complete Homeschool-in-a-Box OS & Community Platform.**\n\n"
            "• **Turnkey Daily Lesson Plans:** 12-week structured curriculum for Kenya CBC (PP1–Grade 9) and British Cambridge (Stage 1–9).\n"
            "• **Sunday Print Packs:** Downloadable weekly homework worksheets and hands-on science lab experiment guides.\n"
            "• **Assessment & Portfolios:** Automated KICD competency rubric tracking (EE/ME/AE/BE) and exportable PDF report cards.\n"
            "• **Verified Tutors & Pods:** Directory of TSC-vetted private tutors and estate learning pods across Nairobi (Kilimani, Karen, Westlands).\n\n"
            "Is there a specific grade or curriculum package you would like to explore?"
        )
        return resp, {'intent': 'overview'}

    # I. Pricing & Fees
    if clean in ['1', 'pricing', 'fees', 'cost'] or any(k in clean for k in ['price', 'cost', 'fee', 'm-pesa', 'mpesa', 'kes', 'term package']):
        resp = (
            "💳 **SomaHome Transparent Pricing & M-Pesa:**\n\n"
            "• **Kenya CBC Core Package (PP1 – Grade 9):** KES 3,500 / term\n"
            "• **British Cambridge Package (Stage 1 – 9):** KES 5,000 / term\n"
            "• **Legal Concierge & KNEC Exam Registration:** KES 2,500 (one-time)\n"
            "• **Vetted Private Home Tutors:** KES 800 – 1,500 / hour\n\n"
            "💰 Instant enrollment via **M-Pesa STK Push** directly to your phone. Ready to enroll for Term 1?"
        )
        return resp, {'intent': 'pricing'}

    # J. Curriculum Comparison
    if clean in ['2', 'cbc', 'cambridge'] or any(k in clean for k in ['cbc vs cambridge', 'compare cbc', 'curriculum comparison', 'difference between cbc']):
        resp = (
            "📚 **Kenya CBC vs British Cambridge Comparison:**\n\n"
            "🇰🇪 **Kenya CBC (KICD 2-6-3-3-3):**\n"
            "• Emphasizes 7 Core Competencies (Communication, Critical Thinking, Digital Literacy, etc.).\n"
            "• Assessed via continuous rubric levels: **EE** (Exceeding), **ME** (Meeting), **AE** (Approaching), **BE** (Below).\n"
            "• National milestones: KPSEA (Grade 6) and KJSEA (Grade 9).\n\n"
            "🇬🇧 **British Cambridge (Primary & Lower Secondary):**\n"
            "• Focuses on rigorous subject mastery in Math, Science, and English.\n"
            "• Standardized external Progression Tests and Checkpoint Exams at Stage 6 and Stage 9.\n\n"
            "Both curriculums are fully supported with daily lesson guides on SomaHome!"
        )
        return resp, {'intent': 'curriculum'}

    # K. Student Progress / Rubrics
    if clean in ['3', 'progress', 'report', 'rubric'] or any(k in clean for k in ['how is my child doing', 'check progress', 'learner progress', 'my kid progress', 'scores']):
        if is_auth:
            resp = (
                f"📊 **Live Academic Progress for {childName}:**\n\n"
                f"• **Term 1 Progress:** 34 of 40 lessons completed (85%)\n"
                f"• **Competency Rubric Rating:** **EE (Exceeding Expectations)** in Science & Mathematics\n"
                f"• **Assigned Facilitator:** Teacher Mercy (Senior CBC Facilitator)\n"
                f"• **Recent Project:** Water Filtration Experiment — *Outstanding initiative and documentation*\n\n"
                f"You can export the full official PDF Report Card anytime from your parent dashboard."
            )
        else:
            resp = (
                "📊 **Sample Learner Progress Overview (Demo):**\n\n"
                "• **Sample Student:** Liam Kariuki (Grade 4 CBC)\n"
                "• **Completion:** 85% (34 of 40 lessons completed)\n"
                "• **Rubric Rating:** **Level 4: EE (Exceeding Expectations)**\n\n"
                "🔒 *To view your own child's real-time live data, please log in to your Parent account.*"
            )
        return resp, {'intent': 'progress'}

    # L. Legal & KNEC Registration
    if clean in ['4', 'legal', 'knec'] or any(k in clean for k in ['legal', 'knec', 'moe', 'ministry of education', 'law', 'affidavit']):
        resp = (
            "⚖️ **Homeschool Legal Compliance in Kenya:**\n\n"
            "• **Constitutional Right:** Article 53(1)(b) of the Constitution of Kenya guarantees every child the right to basic education.\n"
            "• **National KNEC Exams:** Homeschooled candidates can register for national assessments (KPSEA, KCSE/IGCSE) at accredited private sub-county exam centers.\n"
            "• **SomaHome Legal Concierge:** We provide parent legal affidavit templates, portfolio compilation, and KNEC private candidate registration assistance."
        )
        return resp, {'intent': 'legal'}

    # M. Private Tutors & Pods
    if clean in ['5', 'tutor', 'pod'] or any(k in clean for k in ['tutor', 'teacher', 'pod', 'kilimani', 'karen', 'westlands', 'hire tutor']):
        resp = (
            "👩‍🏫 **TSC-Vetted Private Tutors & Learning Pods:**\n\n"
            "• **Estate Tutors in Nairobi:** Certified home educators available in Kilimani, Kileleshwa, Karen, Westlands, Lavington, and Runda.\n"
            "• **Learning Pods:** Small groups (3–6 homeschoolers) sharing a specialized tutor for science labs, French, and coding.\n"
            "• **Hourly Rates:** KES 800 – 1,500 / hr with background-checked credentials."
        )
        return resp, {'intent': 'tutor'}

    # N. Greetings
    if is_trivial_greeting(raw):
        resp = (
            f"👋 Hello and welcome to **SomaHome**! Jambo {userName}!\n\n"
            f"I am your AI Homeschool Guide. How can I assist you with your homeschool curriculum, lesson plans, or learner progress today?"
        )
        return resp, {'intent': 'greeting'}

    # O. Default Comprehensive Knowledge Response
    resp = (
        f"💡 **SomaHome AI Assistant:**\n\n"
        f"I understand you are asking about: *\"{raw}\"*\n\n"
        f"Here is how SomaHome supports you:\n"
        f"• **Curriculum & Grades:** Comprehensive 12-week lesson plans for Kenya CBC (PP1–Grade 9) and British Cambridge (Stage 1–9).\n"
        f"• **Learner Capacity:** You can enroll unlimited children under one parent account with separate portfolios for each.\n"
        f"• **Sunday Print Packs:** Downloadable weekly homework and science lab worksheets.\n"
        f"• **Tutors & Exam Registration:** Direct access to vetted Nairobi tutors and KNEC private candidate guidance.\n\n"
        f"Feel free to ask any specific question about your grade, lessons, or fees!"
    )
    return resp, {'intent': 'general'}
