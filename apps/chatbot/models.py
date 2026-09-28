from django.db import models
from apps.core.models import User, Student

class ChatConversation(models.Model):
    USER_TYPE_CHOICES = (
        ("GUEST", "Guest / Public Visitor"),
        ("PARENT", "Parent"),
        ("STUDENT", "Student"),
        ("TUTOR", "Tutor"),
        ("ADMIN", "Admin / Super Admin"),
    )

    CATEGORY_CHOICES = (
        ("GENERAL", "General Inquiries"),
        ("CURRICULUM_INQUIRY", "Curriculum & CBC/Cambridge"),
        ("PRICING_PAYMENT", "Pricing & M-Pesa Payments"),
        ("STUDENT_PROGRESS", "Student Activity & Progress"),
        ("LEGAL_HOMESCHOOLING", "Legal & Registration Concierge"),
        ("TECHNICAL_HELP", "Technical Support"),
    )

    SENTIMENT_CHOICES = (
        ("POSITIVE", "Positive / Satisfied"),
        ("NEUTRAL", "Neutral / Information Seeking"),
        ("NEEDS_ATTENTION", "Needs Attention / Follow-up"),
        ("FEATURE_REQUEST", "Improvement / Feature Request"),
    )

    session_id = models.CharField(max_length=100, db_index=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="chat_conversations")
    student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True, related_name="chat_conversations")
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default="GUEST")
    guest_name = models.CharField(max_length=100, blank=True, default="Guest Visitor")
    topic_summary = models.CharField(max_length=255, blank=True, default="")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="GENERAL")
    is_meaningful = models.BooleanField(default=False, db_index=True, help_text="True if conversation contains real questions, ignoring basic hi/hello")
    sentiment = models.CharField(max_length=30, choices=SENTIMENT_CHOICES, default="NEUTRAL")
    admin_notes = models.TextField(blank=True, default="")
    is_resolved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user_type} - {self.topic_summary or 'Untitled Session'} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


class ChatMessage(models.Model):
    SENDER_CHOICES = (
        ("USER", "User"),
        ("BOT", "SomaBot Assistant"),
    )

    conversation = models.ForeignKey(ChatConversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    text = models.TextField()
    intent = models.CharField(max_length=50, blank=True, default="inquiry")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.sender}] {self.text[:50]}"
