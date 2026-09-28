import re
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
    elif any(k in lower for k in ["progress", "activity", "lesson", "grade", "score", "rubric", "submission", "complete", "today", "schedule", "report", "homework", "child", "student", "learner", "name", "3"]):
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
        # Provide sample context for demo parent
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
    metadata = {}

    # Numbered Option 1: Pricing & M-Pesa
    if clean in ["1", "one", "number 1", "option 1", "#1", "1."]:
        resp = (
            "?? **SomaHome Package Pricing & M-Pesa Checkout:**\n\n"
            "? **Standard Term Package (CBC / Cambridge):** KES 3,500 ? KES 4,500 per term.\n"
            "? **What is included:**\n"
            "  ? Complete 12-week structured daily lesson plans\n"
            "  ? Weekly Sunday printable worksheets and homework packs\n"
            "  ? Hands-on science lab experiment guides\n"
            "  ? Dedicated WhatsApp mentor support & term report cards\n\n"
            "? **Payment Method:** Instant Safaricom M-Pesa STK Push on checkout."
        )
        return resp, {"topic": "pricing"}

    # Numbered Option 2: Curriculum
    if clean in ["2", "two", "number 2", "option 2", "#2", "2."]:
        resp = (
            "?? **Kenya CBC vs. British Cambridge Curricula:**\n\n"
            "1. **Kenya CBC (Competency Based Curriculum):**\n"
            "   ? Grades: PP1, PP2, Grade 1 through Grade 9 (Junior Secondary).\n"
            "   ? Aligned with KICD standards with 21st-century core competencies, strands, and practical projects.\n\n"
            "2. **British Cambridge International:**\n"
            "   ? Stage 1 to Checkpoint / Lower Secondary & IGCSE preparation.\n"
            "   ? Subjects: English, Mathematics, Science.\n\n"
            "All packages include printable PDFs and rubric assessments."
        )
        return resp, {"topic": "curriculum"}

    # Numbered Option 3: Student Progress / Activity
    if clean in ["3", "three", "number 3", "option 3", "#3", "3."]:
        act_context = get_user_activity_context(user, student)
        resp_parts = ["?? **Latest Homeschool Activity & Rubric Summary:**\n"]
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
        resp_parts.append("\n?? *Tip: You can toggle daily lessons in the Daily OS tab or export PDF report cards in Reports.*")
        return "\n".join(resp_parts), {"activity_checked": True}

    # Numbered Option 4: Legal
    if clean in ["4", "four", "number 4", "option 4", "#4", "4."]:
        resp = (
            "?? **Homeschooling Legality in Kenya & KNEC Registration:**\n\n"
            "? **Constitution of Kenya (Article 53):** Every child has the right to basic education. Alternative learning pathways and homeschooling are recognized.\n"
            "? **KNEC & Assessment:** Learners can register as private candidates for national assessments (KPSEA, KCEN) or Cambridge Checkpoint / IGCSE through registered British Council centers.\n"
            "? **SomaHome Concierge:** We provide formal registration guidance templates and downloadable academic transcripts compliant with Kenyan education standards."
        )
        return resp, {"topic": "legal"}

    # Numbered Option 5: Tutors
    if clean in ["5", "five", "number 5", "option 5", "#5", "5."]:
        resp = (
            "????? **SomaHome Tutor & Learning Pod Marketplace:**\n\n"
            "? Connect with verified, TSC-registered CBC facilitators and Cambridge-certified private tutors.\n"
            "? Available for home 1-on-1 sessions or neighbourhood Learning Pods across Nairobi (Kilimani, Karen, Kileleshwa, Westlands, Runda, Kiambu).\n"
            "? Filter tutors by hourly rate (KES 1,200 - 2,500/hr), curriculum specialty, and verified parent reviews in the Marketplace tab."
        )
        return resp, {"topic": "marketplace"}

    # Greetings Check
    if is_trivial_greeting(clean):
        first_name = (user.first_name or user.username) if user else "Homeschooler"
        greeting_resp = (
            f"Hello {first_name}! ?? I am SomaBot, your AI Homeschool Assistant.\n\n"
            f"Here are common things you can ask me:\n"
            f"1. *\"What are the term package fees and how do I pay with M-Pesa?\"*\n"
            f"2. *\"How does Kenya CBC compare with Cambridge?\"*\n"
            f"3. *\"Check my learner's recent progress and project rubrics\"*\n"
            f"4. *\"How do I register for national KNEC / Cambridge exams?\"*\n"
            f"5. *\"How do I find a vetted home tutor in Nairobi?\"*\n\n"
            f"*(You can simply reply with 1, 2, 3, 4, or 5)*"
        )
        return greeting_resp, {"is_greeting": True}

    # Student Activity / Progress / Child Name Check
    is_asking_activity = any(k in clean for k in [
        "activity", "progress", "score", "grade", "lesson", "how is", "report", "rubric", "submissions", "completed", "doing", "check", "child", "student", "learner", "kid", "called", "name"
    ])

    if is_asking_activity:
        act_context = get_user_activity_context(user, student)
        resp_parts = ["?? **Latest Homeschool Activity & Rubric Summary:**\n"]
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
        resp_parts.append("\n?? *Tip: You can toggle daily lessons in the Daily OS tab or export PDF report cards in Reports.*")
        return "\n".join(resp_parts), {"activity_checked": True}

    # Pricing & M-Pesa
    if any(k in clean for k in ["price", "cost", "fee", "mpesa", "m-pesa", "payment", "kes", "how much"]):
        resp = (
            "?? **SomaHome Package Pricing & M-Pesa Checkout:**\n\n"
            "? **Standard Term Package (CBC / Cambridge):** KES 3,500 ? KES 4,500 per term.\n"
            "? **What is included:**\n"
            "  ? Complete 12-week structured daily lesson plans\n"
            "  ? Weekly Sunday printable worksheets and homework packs\n"
            "  ? Hands-on science lab experiment guides\n"
            "  ? Dedicated WhatsApp mentor support & term report cards\n\n"
            "? **Payment Method:** Instant Safaricom M-Pesa STK Push on checkout."
        )
        return resp, {"topic": "pricing"}

    # Curriculum & CBC vs Cambridge
    if any(k in clean for k in ["cbc", "cambridge", "curriculum", "strand", "subject", "grade", "kindergarten", "high school"]):
        resp = (
            "?? **SomaHome Curriculum Offerings:**\n\n"
            "1. **Kenya CBC (Competency Based Curriculum):**\n"
            "   ? Grades: PP1, PP2, Grade 1 through Grade 9 (Junior Secondary).\n"
            "   ? Aligned with KICD standards with 21st-century core competencies, strands, and practical projects.\n\n"
            "2. **British Cambridge International:**\n"
            "   ? Stage 1 to Checkpoint / Lower Secondary & IGCSE preparation.\n"
            "   ? Subjects: English First/Second Language, Mathematics, Science.\n\n"
            "All packages include printable PDFs, indigenous knowledge integrations, and rubrics."
        )
        return resp, {"topic": "curriculum"}

    # Legal & Registration
    if any(k in clean for k in ["legal", "ministry", "moe", "knec", "law", "affidavit", "register", "legit"]):
        resp = (
            "?? **Homeschooling Legality in Kenya & Legal Concierge:**\n\n"
            "? **Constitution of Kenya (Article 53):** Every child has the right to basic education. Alternative learning pathways and homeschooling are recognized.\n"
            "? **KNEC & Assessment:** Learners can register as private candidates for national assessments (KPSEA, KCEN) or Cambridge Checkpoint / IGCSE through registered British Council centers.\n"
            "? **SomaHome Concierge:** We provide formal registration guidance templates, portfolio trackers, and downloadable academic transcripts compliant with Kenyan education standards."
        )
        return resp, {"topic": "legal"}

    # Tutors & Marketplace
    if any(k in clean for k in ["tutor", "teacher", "pod", "marketplace", "hire", "kilimani", "karen", "westlands"]):
        resp = (
            "????? **SomaHome Tutor & Learning Pod Marketplace:**\n\n"
            "? Connect with verified, TSC-registered CBC facilitators and Cambridge-certified private tutors.\n"
            "? Available for home 1-on-1 sessions or neighbourhood Learning Pods across Nairobi (Kilimani, Karen, Kileleshwa, Westlands, Runda, Kiambu).\n"
            "? Filter tutors by hourly rate (KES 1,200 - 2,500/hr), curriculum specialty, and verified parent reviews in the Marketplace tab."
        )
        return resp, {"topic": "marketplace"}

    # Platform overview / What is soma
    if any(k in clean for k in ["what is soma", "soma", "about", "platform", "website", "explain"]):
        resp = (
            "???? **SomaHome Kenya** is a universal **Homeschool-in-a-Box OS & Community Platform**.\n\n"
            "? **Turnkey Daily Lesson Plans:** 12-week structured curriculum for Kenya CBC (PP1?Grade 9) and British Cambridge.\n"
            "? **Sunday Print Packs:** Downloadable weekly homework worksheets and hands-on science lab experiment guides.\n"
            "? **Assessment & Portfolios:** Automated KICD competency rubric tracking (EE/ME/AE/BE) and ReportLab PDF report cards.\n"
            "? **Verified Tutors:** Directory of TSC-vetted private tutors and estate learning pods across Nairobi (Kilimani, Karen, Westlands)."
        )
        return resp, {"topic": "overview"}

    # General fallback
    fallback = (
        "I am here to assist you with everything related to SomaHome Homeschooling in Kenya! ??\n\n"
        "Here are common things you can ask me:\n"
        "1. *\"What are the term package fees and how do I pay with M-Pesa?\"*\n"
        "2. *\"How does Kenya CBC compare with Cambridge?\"*\n"
        "3. *\"Check my learner's recent progress and project rubrics\"*\n"
        "4. *\"How do I register for national KNEC / Cambridge exams?\"*\n"
        "5. *\"How do I find a vetted home tutor in Nairobi?\"*\n\n"
        "*(You can simply reply with 1, 2, 3, 4, or 5)*"
    )
    return fallback, {"topic": "general_fallback"}
