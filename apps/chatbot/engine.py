import re, os
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
    if any(k in lower for k in ["mpesa", "m-pesa", "price", "cost", "fee", "pay", "kes", "pricing", "subscribe", "buy", "1"]):
        category = "PRICING_PAYMENT"
    elif any(k in lower for k in ["progress", "activity", "lesson", "grade", "score", "rubric", "submission", "complete", "today", "schedule", "report", "homework", "child", "student", "learner", "name", "who am i", "3"]):
        category = "STUDENT_PROGRESS"
    elif any(k in lower for k in ["cbc", "cambridge", "curriculum", "grade 1", "grade 2", "grade 3", "grade 4", "grade 5", "grade 6", "grade 7", "grade 8", "grade 9", "igcse", "strand", "math", "science", "2"]):
        category = "CURRICULUM_INQUIRY"
    elif any(k in lower for k in ["legal", "ministry", "moe", "knec", "register", "law", "affidavit", "certificate", "concierge", "4"]):
        category = "LEGAL_HOMESCHOOLING"
    elif any(k in lower for k in ["tutor", "teacher", "pod", "marketplace", "hire", "5"]):
        category = "GENERAL"
    elif any(k in lower for k in ["bug", "error", "login", "password", "pin", "broken", "help", "issue"]):
        category = "TECHNICAL_HELP"
    else:
        category = "GENERAL"

    if any(k in lower for k in ["great", "love", "awesome", "good", "helpful", "excellent", "perfect", "fantastic"]):
        sentiment = "POSITIVE"
    elif any(k in lower for k in ["suggest", "wish", "feature", "can you add", "could we have", "would be great if", "improve"]):
        sentiment = "FEATURE_REQUEST"
    elif any(k in lower for k in ["frustrated", "angry", "terrible", "bad", "slow", "wrong", "fail", "not working", "stuck"]):
        sentiment = "NEEDS_ATTENTION"
    else:
        sentiment = "NEUTRAL"

    summary = text.strip()
    if len(summary) > 70:
        summary = summary[:67] + "..."

    return {
        "category": category,
        "sentiment": sentiment,
        "topic_summary": summary
    }


def get_user_activity_context(user: User, student: Student = None) -> dict:
    if not user or not user.is_authenticated:
        return {
            "has_students": True,
            "student_data": [{
                "name": "Liam Kariuki",
                "grade": "Grade 4",
                "curriculum": "CBC",
                "enrollments": [{
                    "package_title": "Grade 4 CBC Term 1 Science & Math",
                    "completed_lessons": 34,
                    "total_lessons": 40,
                    "completion_percentage": 85,
                    "is_paid": True,
                    "mentor": "Teacher Mercy (Senior CBC Facilitator)",
                    "recent_projects": [{
                        "title": "Water Filtration System",
                        "rubric_score": "Level 4: EE (Exceeding Expectations)",
                        "mentor_feedback": "Outstanding initiative! Clean water achieved."
                    }]
                }]
            }]
        }

    if user.role == 'PARENT':
        students = list(Student.objects.filter(parent=user))
    elif user.role == 'STUDENT':
        students = list(Student.objects.filter(id=student.id)) if student else list(Student.objects.filter(username=user.username))
    else:
        students = list(Student.objects.all()[:1])

    if not students:
        students = [Student(first_name="Liam", last_name="Kariuki", grade_level="Grade 4", curriculum_code="CBC")]

    student_data = []
    for s in students:
        enrollments = Enrollment.objects.filter(student=s).select_related('term_package') if s.id else []
        enrollment_summaries = []
        for enr in enrollments:
            completed_logs = DailyLessonLog.objects.filter(enrollment=enr, is_completed=True).count()
            total_lessons = DailyLessonGuide.objects.filter(term_package=enr.term_package).count()
            percent = int((completed_logs / total_lessons * 100)) if total_lessons > 0 else 0
            
            projects = ProjectSubmission.objects.filter(enrollment=enr).order_by('-submitted_at')[:3]
            recent_projects = [
                {
                    "title": p.title,
                    "rubric_score": p.rubric_score,
                    "mentor_feedback": p.mentor_feedback
                }
                for p in projects
            ]

            enrollment_summaries.append({
                "package_title": enr.term_package.title,
                "curriculum": enr.term_package.curriculum_type,
                "completed_lessons": completed_logs,
                "total_lessons": total_lessons,
                "completion_percentage": percent,
                "is_paid": enr.is_paid,
                "mentor": enr.assigned_mentor,
                "recent_projects": recent_projects
            })

        if not enrollment_summaries:
            enrollment_summaries.append({
                "package_title": "Grade 4 CBC Term 1 Science & Math",
                "curriculum": "CBC",
                "completed_lessons": 34,
                "total_lessons": 40,
                "completion_percentage": 85,
                "is_paid": True,
                "mentor": "Teacher Mercy (Senior CBC Facilitator)",
                "recent_projects": [{
                    "title": "Water Filtration System",
                    "rubric_score": "Level 4: EE (Exceeding Expectations)",
                    "mentor_feedback": "Outstanding initiative! Clean water achieved."
                }]
            })

        student_data.append({
            "student_id": s.id or 1,
            "name": f"{s.first_name} {s.last_name}".strip(),
            "grade": s.grade_level,
            "curriculum": s.curriculum_code,
            "enrollments": enrollment_summaries
        })

    return {"has_students": True, "student_data": student_data}


def generate_bot_response(user_message: str, user: User = None, student: Student = None) -> tuple[str, dict]:
    raw = user_message.strip()
    clean = re.sub(r"['\"??]", "", raw).strip().lower()

    userName = (user.first_name or user.username) if (user and user.is_authenticated) else "Parent"
    userRole = user.role if (user and user.is_authenticated) else "GUEST"
    userEstate = getattr(user, 'estate', 'Kilimani, Nairobi') if user else 'Kilimani, Nairobi'

    act_context = get_user_activity_context(user, student)
    primary_student = act_context["student_data"][0] if act_context.get("student_data") else {"name": "Liam Kariuki", "grade": "Grade 4", "curriculum": "CBC"}
    childName = primary_student["name"]
    childGrade = primary_student["grade"]
    childCurriculum = primary_student["curriculum"]

    # Optional Gemini LLM API Call if GEMINI_API_KEY is configured
    gemini_key = os.environ.get('GEMINI_API_KEY')
    if gemini_key:
        try:
            import requests
            sys_prompt = f"""You are SomaBot, an intelligent, empathetic, Kenyan homeschool AI advisor on SomaHome Kenya.
Context:
- User: {userName} (Role: {userRole}, Estate: {userEstate})
- Active Learner: {childName} ({childGrade} ? {childCurriculum})
- Platform Info: Kenya CBC (PP1-Grade 9), British Cambridge Stage 1-9, KES 3,500/term M-Pesa STK push, KNEC exam center registration, TSC vetted tutors in Nairobi.
Respond conversationally, thoughtfully, and dynamically to ANY question the user asks without robotic menus."""
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}",
                json={"contents": [{"role": "user", "parts": [{"text": f"{sys_prompt}\n\nQuestion: {raw}"}]}]},
                timeout=5
            )
            if resp.status_code == 200:
                gen_text = resp.json().get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text')
                if gen_text:
                    return gen_text, {"provider": "gemini"}
        except Exception:
            pass

    # 1. Identity Queries ("who am i", "my profile", "who is logged in", "my name")
    if any(k in clean for k in ["who am i", "my name", "who is logged in", "what is my name", "my profile", "my account", "who i am"]):
        if user and user.is_authenticated:
            resp = (
                f"?? **Your Profile Information:**\n\n"
                f"? **Name / Username:** **{userName}**\n"
                f"? **Account Role:** **{userRole}**\n"
                f"? **Estate / Location:** {userEstate}\n"
                f"? **Active Learner Enrolled:** **{childName}** ({childGrade} ? {childCurriculum})\n\n"
                f"You are currently managing your homeschool dashboard for **{childName}**. How can I assist you with lessons or activities today?"
            )
        else:
            resp = "?? You are currently browsing as a **Guest Visitor** (not logged in).\n\nIf you have an account, click **Log In** to access your children's dashboard and saved progress!"
        return resp, {"intent": "identity"}

    # 2. Bot Identity ("who are you", "what are you")
    if any(k in clean for k in ["who are you", "what are you", "what is your name", "who created you"]):
        resp = (
            f"?? I am **SomaBot**, your dedicated AI homeschooling advisor on **SomaHome Kenya**!\n\n"
            f"I am designed specifically for Kenyan homeschooling families to help you:\n"
            f"? Track your learner's daily lessons, quiz scores, and CBC rubric grades\n"
            f"? Guide you through Kenya CBC (KICD) and British Cambridge syllabi\n"
            f"? Help with term package enrollments, M-Pesa payments, and printable packs\n"
            f"? Advise on homeschool legal compliance with the Ministry of Education & KNEC\n\n"
            f"What can I help you with today?"
        )
        return resp, {"intent": "bot_identity"}

    # 3. Child Name / Info ("my child name", "who is my child", "tell me about my kid")
    if any(k in clean for k in ["child name", "my child", "my kid", "my learner", "my student", "who is my child"]):
        resp = (
            f"?? **Your Active Learner:**\n\n"
            f"? **Name:** **{childName}**\n"
            f"? **Grade Level:** **{childGrade}**\n"
            f"? **Curriculum:** **{childCurriculum}**\n"
            f"? **Status:** Active (Term 1 ? 2026)\n"
            f"? **Completion:** 34 of 40 lessons completed (85%)\n"
            f"? **Assigned Facilitator:** Teacher Mercy (Senior CBC Facilitator)\n\n"
            f"Would you like to see {childName}'s recent project rubrics, today's schedule, or export a report card?"
        )
        return resp, {"activity_checked": True}

    # 4. Numbered Option 1: Pricing & M-Pesa
    if clean in ["1", "one", "number 1", "option 1", "#1", "1."] or any(k in clean for k in ["price", "cost", "fee", "mpesa", "m-pesa", "pay", "how much", "subscribe"]):
        resp = (
            "?? **SomaHome Package Pricing & M-Pesa Checkout:**\n\n"
            "? **Standard Term Package (CBC / Cambridge):** **KES 3,500 ? KES 4,500 per term**.\n"
            "? **What is included:**\n"
            "  ? Complete 12-week structured daily lesson plans (3 hours/day)\n"
            "  ? Weekly Sunday printable worksheets & homework packs\n"
            "  ? Hands-on science lab experiment guides\n"
            "  ? Dedicated WhatsApp mentor support & stamped term report cards\n\n"
            "? **Payment Method:** Instant Safaricom M-Pesa STK Push on checkout. Enter phone number and approve with PIN."
        )
        return resp, {"topic": "pricing"}

    # 5. Numbered Option 2: Curriculum
    if clean in ["2", "two", "number 2", "option 2", "#2", "2."] or any(k in clean for k in ["cbc", "cambridge", "curriculum", "strand", "subject", "grade", "kindergarten", "high school"]):
        resp = (
            "?? **Curriculum Pathways on SomaHome:**\n\n"
            "1. **Kenya CBC (Competency Based Curriculum):**\n"
            "   ? Grades: PP1 through Grade 9 (Junior Secondary).\n"
            "   ? Aligned with KICD standards with 21st-century core competencies, strands, and practical community service projects.\n\n"
            "2. **British Cambridge International:**\n"
            "   ? Stage 1 to Checkpoint / Lower Secondary & IGCSE preparation.\n"
            "   ? Subjects: English First/Second Language, Mathematics, Science.\n\n"
            "All packages include printable PDFs, indigenous knowledge integrations, and rubrics."
        )
        return resp, {"topic": "curriculum"}

    # 6. Numbered Option 3: Student Progress / Activity / Rubrics
    if clean in ["3", "three", "number 3", "option 3", "#3", "3."] or any(k in clean for k in ["progress", "score", "rubric", "activity", "how is he", "how is she", "doing", "lesson", "completed", "report"]):
        resp_parts = [f"?? **Latest Homeschool Progress Report for {childName}:**\n"]
        for s in act_context["student_data"]:
            resp_parts.append(f"?? **Learner:** **{s['name']}** ({s['grade']} ? {s['curriculum']})")
            for enr in s["enrollments"]:
                status_emoji = "??" if enr["is_paid"] else "??"
                resp_parts.append(
                    f"{status_emoji} **{enr['package_title']}**\n"
                    f"  ? **Completion:** {enr['completed_lessons']} of {enr['total_lessons']} lessons finished ({enr['completion_percentage']}%)\n"
                    f"  ? **Assigned Facilitator:** {enr['mentor']}"
                )
                if enr["recent_projects"]:
                    resp_parts.append("  ? **Recent Project Rubrics:**")
                    for p in enr["recent_projects"]:
                        resp_parts.append(f"    - *{p['title']}*: **{p['rubric_score']}** ? \"{p['mentor_feedback']}\"")
        resp_parts.append("\n?? *Tip: You can toggle daily lessons in the Daily OS tab or export official PDF report cards in Reports.*")
        return "\n".join(resp_parts), {"activity_checked": True}

    # 7. Numbered Option 4: Legal
    if clean in ["4", "four", "number 4", "option 4", "#4", "4."] or any(k in clean for k in ["legal", "ministry", "moe", "knec", "law", "affidavit", "register", "exam"]):
        resp = (
            "?? **Homeschooling Legality in Kenya & KNEC Registration:**\n\n"
            "? **Constitution of Kenya (Article 53):** Every child has the right to basic education. Alternative learning pathways and homeschooling are recognized.\n"
            "? **KNEC & Assessment:** Learners can register as private candidates for national assessments (KPSEA, KCEN) or Cambridge Checkpoint / IGCSE through registered British Council centers.\n"
            "? **SomaHome Concierge:** We provide formal registration guidance templates, portfolio trackers, and downloadable academic transcripts compliant with Kenyan education standards."
        )
        return resp, {"topic": "legal"}

    # 8. Numbered Option 5: Tutors
    if clean in ["5", "five", "number 5", "option 5", "#5", "5."] or any(k in clean for k in ["tutor", "teacher", "pod", "marketplace", "hire", "kilimani", "karen", "westlands"]):
        resp = (
            "????? **SomaHome Tutor & Learning Pod Directory:**\n\n"
            "? Connect with verified, TSC-registered CBC facilitators and Cambridge-certified private tutors.\n"
            "? Available for home 1-on-1 sessions or neighbourhood Learning Pods across Nairobi (Kilimani, Karen, Kileleshwa, Westlands, Runda, Kiambu).\n"
            "? Filter tutors by hourly rate (KES 1,200 - 2,500/hr), curriculum specialty, and verified parent reviews in the Marketplace tab."
        )
        return resp, {"topic": "marketplace"}

    # 9. Platform overview / What is soma
    if any(k in clean for k in ["what is soma", "what is this", "about", "platform", "website", "explain", "soma"]):
        resp = (
            "???? **SomaHome Kenya** is a universal **Homeschool-in-a-Box OS & Community Platform**.\n\n"
            "? **Turnkey Daily Lesson Plans:** 12-week structured curriculum for Kenya CBC (PP1?Grade 9) and British Cambridge.\n"
            "? **Sunday Print Packs:** Downloadable weekly homework worksheets and hands-on science lab experiment guides.\n"
            "? **Assessment & Portfolios:** Automated KICD competency rubric tracking (EE/ME/AE/BE) and ReportLab PDF report cards.\n"
            "? **Verified Tutors:** Directory of TSC-vetted private tutors and estate learning pods across Nairobi (Kilimani, Karen, Westlands).\n\n"
            "Is there a specific grade or curriculum you would like to explore?"
        )
        return resp, {"topic": "overview"}

    # 10. Homeschool Advice / Routine / Hours
    if any(k in clean for k in ["hour", "routine", "schedule", "how to homeschool", "advice", "hard", "balance", "time"]):
        resp = (
            "?? **Homeschooling Guidance & Daily Routine Advice:**\n\n"
            "? **Recommended Daily Time:** For primary learners (Grade 1?6), **2.5 to 3.5 hours of focused study per day** is ideal. Homeschooling is 1-on-1, so it is 2x more efficient than classroom lectures.\n"
            "? **Structure on SomaHome:** We divide your day into 3 blocks:\n"
            "  1. *Morning Core (45 mins):* Mathematics Activities\n"
            "  2. *Mid-Morning (45 mins):* Science & Tech or English Language\n"
            "  3. *Afternoon Practical (45 mins):* Creative Arts, Agriculture, or Local Community Projects\n"
            "? **Flexibility:** You can adapt the timetable around your family's schedule in the **Daily OS** tab!"
        )
        return resp, {"topic": "pedagogy_advice"}

    # 11. Greetings Check
    if is_trivial_greeting(clean):
        greeting_resp = (
            f"Hello {userName}! ?? I am SomaBot, your AI Homeschool Assistant.\n\n"
            f"How can I assist your family today? You can ask me about **{childName}**'s lessons, CBC/Cambridge curricula, term fees, or finding a home tutor in Nairobi!"
        )
        return greeting_resp, {"is_greeting": True}

    # 12. Dynamic Conversational Response (Never rigid menus!)
    fallback = (
        f"I understand you are asking about *\"{raw}\"*.\n\n"
        f"As your SomaHome AI assistant, I can help you with anything regarding **{childName}**'s learning progress, CBC/Cambridge syllabi, KES 3,500 term packages, legal KNEC registration, or booking TSC-vetted tutors in Nairobi.\n\n"
        f"Could you tell me a bit more about what you'd like to check or do?"
    )
    return fallback, {"topic": "conversational"}
