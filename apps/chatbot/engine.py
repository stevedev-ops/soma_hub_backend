import re
from datetime import date
from django.db.models import Count, Q
from apps.core.models import Student, User
from apps.tracker.models import Enrollment, DailyLessonLog, ProjectSubmission
from apps.curriculum.models import TermPackage, DailyLessonGuide

# Regular expressions for trivial greetings & chit-chat
TRIVIAL_GREETING_PATTERNS = [
    r"^(hi|hello|hey|yo|habari|mambo|sasa|jambo|sup|howdy|hola|greetings)\b",
    r"^good\s*(morning|afternoon|evening|day)\b",
    r"^(test|testing|123|check)\b",
    r"^(bye|goodbye|cya|see you|later|good night)\b",
    r"^(thanks|thank you|asante|asante sana|ok|okay|cool|k|alright)\b"
]

def is_trivial_greeting(text: str) -> bool:
    """
    Returns True if the text is simply a greeting or chit-chat without a real question/inquiry.
    """
    clean = text.strip().lower()
    # Remove punctuation
    clean_no_punct = re.sub(r'[^\w\s]', '', clean)
    
    # If the message is long (> 6 words), it's likely a real question even if it starts with 'hi'
    words = clean_no_punct.split()
    if len(words) > 6:
        return False

    for pattern in TRIVIAL_GREETING_PATTERNS:
        if re.search(pattern, clean_no_punct):
            # If the entire message is just the greeting or under 4 words, mark as trivial
            if len(words) <= 4:
                return True
    return False


def classify_conversation(text: str) -> dict:
    """
    Classifies the user inquiry into category, sentiment, and summary topic.
    """
    lower = text.lower()

    # Category Detection
    if any(k in lower for k in ["mpesa", "m-pesa", "price", "cost", "fee", "pay", "kes", "pricing", "subscribe", "buy"]):
        category = "PRICING_PAYMENT"
    elif any(k in lower for k in ["progress", "activity", "lesson", "grade", "score", "rubric", "submission", "complete", "today", "schedule", "report", "homework", "child", "student"]):
        category = "STUDENT_PROGRESS"
    elif any(k in lower for k in ["cbc", "cambridge", "curriculum", "grade 1", "grade 2", "grade 3", "grade 4", "grade 5", "grade 6", "grade 7", "grade 8", "grade 9", "igcse", "strand", "math", "science"]):
        category = "CURRICULUM_INQUIRY"
    elif any(k in lower for k in ["legal", "ministry", "moe", "knec", "register", "law", "affidavit", "certificate", "concierge"]):
        category = "LEGAL_HOMESCHOOLING"
    elif any(k in lower for k in ["bug", "error", "login", "password", "pin", "broken", "help", "issue"]):
        category = "TECHNICAL_HELP"
    else:
        category = "GENERAL"

    # Sentiment Detection
    if any(k in lower for k in ["great", "love", "awesome", "good", "helpful", "excellent", "perfect", "fantastic"]):
        sentiment = "POSITIVE"
    elif any(k in lower for k in ["suggest", "wish", "feature", "can you add", "could we have", "would be great if", "improve"]):
        sentiment = "FEATURE_REQUEST"
    elif any(k in lower for k in ["frustrated", "angry", "terrible", "bad", "slow", "wrong", "fail", "not working", "stuck"]):
        sentiment = "NEEDS_ATTENTION"
    else:
        sentiment = "NEUTRAL"

    # Topic Summary Generator (concise clean label)
    summary = text.strip()
    if len(summary) > 70:
        summary = summary[:67] + "..."

    return {
        "category": category,
        "sentiment": sentiment,
        "topic_summary": summary
    }


def get_user_activity_context(user: User, student: Student = None) -> dict:
    """
    Fetches real-time student activity, completed lessons, enrollment status, and project submissions.
    """
    if not user or not user.is_authenticated:
        return {}

    # Find students for parent or user itself
    if user.role == 'PARENT':
        students = list(Student.objects.filter(parent=user))
    elif user.role == 'STUDENT':
        students = list(Student.objects.filter(id=student.id)) if student else list(Student.objects.filter(username=user.username))
    else:
        students = []

    if not students:
        return {"has_students": False, "student_data": []}

    student_data = []
    for s in students:
        enrollments = Enrollment.objects.filter(student=s).select_related('term_package')
        enrollment_summaries = []
        for enr in enrollments:
            completed_logs = DailyLessonLog.objects.filter(enrollment=enr, is_completed=True).count()
            total_lessons = DailyLessonGuide.objects.filter(term_package=enr.term_package).count()
            percent = int((completed_logs / total_lessons * 100)) if total_lessons > 0 else 0
            
            # Latest projects
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

        student_data.append({
            "student_id": s.id,
            "name": f"{s.first_name} {s.last_name}".strip(),
            "grade": s.grade_level,
            "curriculum": s.curriculum_code,
            "pin": s.pin_code,
            "enrollments": enrollment_summaries
        })

    return {"has_students": True, "student_data": student_data}


def generate_bot_response(user_message: str, user: User = None, student: Student = None) -> tuple[str, dict]:
    """
    Generates an intelligent context-aware response for SomaHome homeschoolers.
    Returns (response_text, metadata_dict).
    """
    clean_msg = user_message.strip()
    lower_msg = clean_msg.lower()
    metadata = {}

    # Check if trivial greeting
    if is_trivial_greeting(clean_msg):
        if user and user.is_authenticated:
            first_name = user.first_name or user.username
            greeting_resp = (
                f"Hello {first_name}! ?? I am SomaBot, your personal homeschooling assistant.\n\n"
                f"I can help you check your student's daily lesson progress, upcoming projects, term reports, "
                f"or answer questions about CBC and Cambridge curricula. How can I support your homeschool today?"
            )
        else:
            greeting_resp = (
                "Hello and welcome to SomaHome! ??????\n\n"
                "I am your AI Homeschool Guide. I can help you with:\n"
                "? **Curriculum Packages** (Kenya CBC & British Cambridge Stage 1-9)\n"
                "? **Pricing & M-Pesa** (Instant term enrollment from KES 3,500)\n"
                "? **Legal Homeschool Concierge** (MOE & KNEC guidance)\n"
                "? **Private Tutors & Learning Pods** in Nairobi\n\n"
                "What would you like to explore?"
            )
        return greeting_resp, {"is_greeting": True}

    # Authenticated user asking about student activity / progress
    is_asking_activity = any(k in lower_msg for k in [
        "activity", "progress", "score", "grade", "lesson", "how is", "report", "rubric", "submissions", "completed", "doing", "check"
    ])

    if user and user.is_authenticated and is_asking_activity:
        act_context = get_user_activity_context(user, student)
        if act_context.get("has_students") and act_context["student_data"]:
            metadata["activity_checked"] = True
            metadata["student_count"] = len(act_context["student_data"])
            
            resp_parts = ["?? **Here is the latest Homeschool Activity Summary:**\n"]
            for s in act_context["student_data"]:
                resp_parts.append(f"?? **Learner:** {s['name']} ({s['grade']} ? {s['curriculum']})")
                if s["enrollments"]:
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
                else:
                    resp_parts.append("  *(No active term packages enrolled yet. You can enroll in Term Packages from the Dashboard!)*")
                resp_parts.append("")

            resp_parts.append("?? *Tip: You can toggle daily lesson checkboxes in the Daily OS tab or generate official PDF report cards in Reports.*")
            return "\n".join(resp_parts), metadata

    # Pricing & M-Pesa Payment questions
    if any(k in lower_msg for k in ["price", "cost", "fee", "mpesa", "m-pesa", "payment", "kes", "how much"]):
        resp = (
            "?? **SomaHome Package Pricing & M-Pesa Checkout:**\n\n"
            "? **Standard Term Package (CBC / Cambridge):** KES 3,500 ? KES 4,500 per term.\n"
            "? **What is included:**\n"
            "  ? Complete 12-week structured daily lesson plans\n"
            "  ? Weekly Sunday printable worksheets and homework packs\n"
            "  ? Hands-on science lab experiment guides\n"
            "  ? Dedicated WhatsApp mentor support & term report cards\n\n"
            "? **Payment Method:** Instant Safaricom M-Pesa STK Push. Enter your phone number (e.g., 0712345678) on checkout and approve with your M-Pesa PIN on your phone."
        )
        return resp, {"topic": "pricing"}

    # Curriculum & CBC / Cambridge questions
    if any(k in lower_msg for k in ["cbc", "cambridge", "curriculum", "strand", "subject", "grade", "kindergarten", "high school"]):
        resp = (
            "?? **SomaHome Curriculum Offerings:**\n\n"
            "1. **Kenya CBC (Competency Based Curriculum):**\n"
            "   ? Grades: PP1, PP2, Grade 1 through Grade 9 (Junior Secondary).\n"
            "   ? Aligned with KICD standards with 21st-century core competencies, strands, substrands, and practical local community service projects.\n\n"
            "2. **British Cambridge International:**\n"
            "   ? Stage 1 to Checkpoint / Lower Secondary & IGCSE preparation.\n"
            "   ? Subjects: English First/Second Language, Cambridge Primary Mathematics, Cambridge Science.\n\n"
            "All lessons include printable PDF materials, indigenous knowledge integrations, and rubrics."
        )
        return resp, {"topic": "curriculum"}

    # Legal & Registration Concierge
    if any(k in lower_msg for k in ["legal", "ministry", "moe", "knec", "law", "affidavit", "register", "legit", "legal concierge"]):
        resp = (
            "?? **Homeschooling Legality in Kenya & Legal Concierge:**\n\n"
            "? **Constitution of Kenya (Article 53):** Every child has the right to basic education. Alternative learning pathways and homeschooling are legally recognized.\n"
            "? **KNEC & Assessment:** Learners can register as private candidates for national assessments (KPSEA, KCEN) or Cambridge Checkpoint / IGCSE through registered British Council centers.\n"
            "? **SomaHome Concierge:** We provide formal registration guidance templates, portfolio trackers, and downloadable academic transcripts compliant with Kenyan education standards."
        )
        return resp, {"topic": "legal"}

    # Tutor & Marketplace questions
    if any(k in lower_msg for k in ["tutor", "teacher", "pod", "marketplace", "hire", "kilimani", "karen", "westlands"]):
        resp = (
            "????? **SomaHome Tutor & Learning Pod Marketplace:**\n\n"
            "? Connect with verified, TSC-registered CBC facilitators and Cambridge-certified private tutors.\n"
            "? Available for home 1-on-1 sessions or neighbourhood Learning Pods across Nairobi (Kilimani, Karen, Kileleshwa, Westlands, Runda, Kiambu).\n"
            "? Filter tutors by hourly rate (KES 1,200 - 2,500/hr), curriculum specialty, and verified parent reviews in the Marketplace tab."
        )
        return resp, {"topic": "marketplace"}

    # General fallback with actionable helpful guidance
    fallback = (
        "I am here to assist you with everything related to SomaHome Homeschooling in Kenya! ??\n\n"
        "Here are common things you can ask me:\n"
        "1. *\"What are the term package fees and how do I pay with M-Pesa?\"*\n"
        "2. *\"How does Kenya CBC compare with Cambridge on this platform?\"*\n"
        "3. *\"Check my learner's recent progress and project rubrics\"*\n"
        "4. *\"How do I register for national KNEC / Cambridge exams?\"*\n"
        "5. *\"How do I find a vetted home tutor in Nairobi?\"*\n\n"
        "Please feel free to ask your specific question!"
    )
    return fallback, {"topic": "general_fallback"}
