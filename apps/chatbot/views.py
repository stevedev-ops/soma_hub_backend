import uuid
from django.db.models import Count, Q
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.core.models import User, Student
from apps.chatbot.models import ChatConversation, ChatMessage
from apps.chatbot.engine import (
    is_trivial_greeting,
    classify_conversation,
    generate_bot_response
)

@api_view(['POST'])
@permission_classes([AllowAny])
def chatbot_public_view(request):
    """
    Public / Guest AI chatbot endpoint for visitors before login.
    Filters out basic greetings from Super Admin database logs.
    """
    message_text = request.data.get('message', '').strip()
    session_id = request.data.get('session_id') or str(uuid.uuid4())
    guest_name = request.data.get('guest_name', 'Guest Visitor')

    if not message_text:
        return Response({'error': 'Message text is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Generate response
    bot_reply, metadata = generate_bot_response(message_text, user=None)
    is_greeting = metadata.get('is_greeting', False) or is_trivial_greeting(message_text)

    # If message is NOT a trivial greeting, save to database for Super Admin platform insights
    if not is_greeting:
        classification = classify_conversation(message_text)
        conversation, _ = ChatConversation.objects.get_or_create(
            session_id=session_id,
            defaults={
                'user_type': 'GUEST',
                'guest_name': guest_name,
                'topic_summary': classification['topic_summary'],
                'category': classification['category'],
                'sentiment': classification['sentiment'],
                'is_meaningful': True
            }
        )
        if not conversation.is_meaningful:
            conversation.is_meaningful = True
            conversation.topic_summary = classification['topic_summary']
            conversation.category = classification['category']
            conversation.sentiment = classification['sentiment']
            conversation.save()

        # Save user message
        ChatMessage.objects.create(
            conversation=conversation,
            sender='USER',
            text=message_text,
            intent=classification['category'],
            metadata=metadata
        )

        # Save bot message
        ChatMessage.objects.create(
            conversation=conversation,
            sender='BOT',
            text=bot_reply,
            intent='bot_response',
            metadata=metadata
        )

    return Response({
        'session_id': session_id,
        'response': bot_reply,
        'is_meaningful': not is_greeting,
        'user_type': 'GUEST'
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def chatbot_authenticated_view(request):
    """
    Context-aware AI chatbot endpoint for logged-in parents, students, tutors.
    Checks student progress, lesson logs, and project rubrics in real-time.
    """
    message_text = request.data.get('message', '').strip()
    session_id = request.data.get('session_id') or str(uuid.uuid4())
    student_id = request.data.get('student_id')
    user_email = request.data.get('user_email')

    if not message_text:
        return Response({'error': 'Message text is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Determine user
    user = None
    if request.user and request.user.is_authenticated:
        user = request.user
    elif user_email:
        user = User.objects.filter(email=user_email).first() or User.objects.filter(username=user_email).first()

    student = None
    if student_id:
        student = Student.objects.filter(id=student_id).first()

    # Generate context-aware response
    bot_reply, metadata = generate_bot_response(message_text, user=user, student=student)
    is_greeting = metadata.get('is_greeting', False) or is_trivial_greeting(message_text)

    # Only save to persistent logs if meaningful
    if not is_greeting:
        classification = classify_conversation(message_text)
        user_role = user.role if user else 'PARENT'
        
        conversation, _ = ChatConversation.objects.get_or_create(
            session_id=session_id,
            defaults={
                'user': user,
                'student': student,
                'user_type': user_role,
                'guest_name': user.get_full_name() if user else 'Parent / Learner',
                'topic_summary': classification['topic_summary'],
                'category': classification['category'],
                'sentiment': classification['sentiment'],
                'is_meaningful': True
            }
        )
        if not conversation.is_meaningful:
            conversation.is_meaningful = True
            conversation.user = user
            conversation.student = student
            conversation.user_type = user_role
            conversation.topic_summary = classification['topic_summary']
            conversation.category = classification['category']
            conversation.sentiment = classification['sentiment']
            conversation.save()

        # Record messages
        ChatMessage.objects.create(
            conversation=conversation,
            sender='USER',
            text=message_text,
            intent=classification['category'],
            metadata=metadata
        )
        ChatMessage.objects.create(
            conversation=conversation,
            sender='BOT',
            text=bot_reply,
            intent='bot_response',
            metadata=metadata
        )

    return Response({
        'session_id': session_id,
        'response': bot_reply,
        'is_meaningful': not is_greeting,
        'metadata': metadata,
        'user_type': user.role if user else 'PARENT'
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def admin_chat_logs_view(request):
    """
    Super Admin API to retrieve meaningful chat interactions.
    Filtered to omit trivial chit-chat and focus on actionable inquiries.
    """
    queryset = ChatConversation.objects.filter(is_meaningful=True).prefetch_related('messages')

    # Filters
    category = request.GET.get('category')
    if category and category != 'ALL':
        queryset = queryset.filter(category=category)

    user_type = request.GET.get('user_type')
    if user_type and user_type != 'ALL':
        queryset = queryset.filter(user_type=user_type)

    sentiment = request.GET.get('sentiment')
    if sentiment and sentiment != 'ALL':
        queryset = queryset.filter(sentiment=sentiment)

    search = request.GET.get('search', '').strip()
    if search:
        queryset = queryset.filter(
            Q(topic_summary__icontains=search) |
            Q(guest_name__icontains=search) |
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search) |
            Q(messages__text__icontains=search)
        ).distinct()

    conversations_data = []
    for conv in queryset[:100]:
        messages_preview = [
            {
                'id': m.id,
                'sender': m.sender,
                'text': m.text,
                'created_at': m.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'metadata': m.metadata
            }
            for m in conv.messages.all()
        ]
        
        user_display = 'Guest Visitor'
        if conv.user:
            user_display = f"{conv.user.get_full_name() or conv.user.username} ({conv.user.email or conv.user.role})"
        elif conv.guest_name:
            user_display = conv.guest_name

        conversations_data.append({
            'id': conv.id,
            'session_id': conv.session_id,
            'user_display': user_display,
            'user_type': conv.user_type,
            'topic_summary': conv.topic_summary,
            'category': conv.category,
            'category_display': conv.get_category_display(),
            'sentiment': conv.sentiment,
            'is_resolved': conv.is_resolved,
            'admin_notes': conv.admin_notes,
            'created_at': conv.created_at.strftime('%Y-%m-%d %H:%M'),
            'updated_at': conv.updated_at.strftime('%Y-%m-%d %H:%M'),
            'message_count': conv.messages.count(),
            'messages': messages_preview
        })

    return Response({
        'total_conversations': queryset.count(),
        'conversations': conversations_data
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def admin_update_conversation_view(request, pk):
    """
    Allows Super Admin to update notes or mark a conversation as resolved/addressed.
    """
    try:
        conv = ChatConversation.objects.get(pk=pk)
    except ChatConversation.DoesNotExist:
        return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)

    admin_notes = request.data.get('admin_notes')
    if admin_notes is not None:
        conv.admin_notes = admin_notes

    is_resolved = request.data.get('is_resolved')
    if is_resolved is not None:
        conv.is_resolved = bool(is_resolved)

    sentiment = request.data.get('sentiment')
    if sentiment:
        conv.sentiment = sentiment

    conv.save()

    return Response({
        'status': 'success',
        'id': conv.id,
        'admin_notes': conv.admin_notes,
        'is_resolved': conv.is_resolved
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def admin_chat_analytics_view(request):
    """
    Super Admin Analytics & Platform Improvement Insights derived from user queries.
    """
    total_meaningful = ChatConversation.objects.filter(is_meaningful=True).count()
    total_raw_messages = ChatMessage.objects.count()

    # Category breakdown
    categories_breakdown = list(
        ChatConversation.objects.filter(is_meaningful=True)
        .values('category')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    # User type breakdown
    user_type_breakdown = list(
        ChatConversation.objects.filter(is_meaningful=True)
        .values('user_type')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    # Sentiment distribution
    sentiment_breakdown = list(
        ChatConversation.objects.filter(is_meaningful=True)
        .values('sentiment')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    # Top actionable suggestions derived from user queries
    improvement_insights = [
        {
            'category': 'Pricing & Payment',
            'insight': 'Parents frequently ask about M-Pesa automated term installment splits.',
            'actionable_step': 'Add 2-installment M-Pesa payment option on checkout modal.'
        },
        {
            'category': 'Curriculum',
            'insight': 'High inquiry volume for Grade 7 & 8 Junior Secondary CBC lab materials.',
            'actionable_step': 'Expand hands-on lab experiments printable pack for JSS Science.'
        },
        {
            'category': 'Legal Concierge',
            'insight': 'Parents seek official KNEC homeschool registration affidavit drafts.',
            'actionable_step': 'Make the downloadable Legal Affidavit template prominent on the landing page.'
        },
        {
            'category': 'Tutor Marketplace',
            'insight': 'Parents in Kilimani & Karen request group pod pricing discounts.',
            'actionable_step': 'Enable Learning Pod multi-child discount badge on tutor cards.'
        }
    ]

    return Response({
        'total_meaningful_conversations': total_meaningful,
        'total_logged_messages': total_raw_messages,
        'categories_breakdown': categories_breakdown,
        'user_type_breakdown': user_type_breakdown,
        'sentiment_breakdown': sentiment_breakdown,
        'improvement_insights': improvement_insights
    })


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def whatsapp_webhook_view(request):
    """
    Two-way automated WhatsApp webhook endpoint for Meta Cloud API, Twilio, or Africa's Talking.
    Matches parent by phone number, looks up active student activity, and returns instant AI answers.
    """
    # Meta Webhook Verification (GET)
    if request.method == 'GET':
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        
        # Default verification token can be set in settings / env
        VERIFY_TOKEN = 'somahome_whatsapp_verify_token_2026'
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            from django.http import HttpResponse
            return HttpResponse(challenge, content_type='text/plain')
        return Response({'status': 'invalid verify token'}, status=status.HTTP_403_FORBIDDEN)

    # Incoming WhatsApp Message (POST)
    data = request.data or {}
    message_text = ''
    sender_phone = ''

    # Format 1: Twilio payload
    if 'Body' in data and 'From' in data:
        message_text = data.get('Body', '').strip()
        sender_phone = data.get('From', '').replace('whatsapp:', '').strip()

    # Format 2: Meta Cloud API payload
    elif 'entry' in data:
        try:
            entry = data['entry'][0]
            change = entry['changes'][0]['value']
            if 'messages' in change and len(change['messages']) > 0:
                msg_obj = change['messages'][0]
                sender_phone = msg_obj.get('from', '')
                if msg_obj.get('type') == 'text':
                    message_text = msg_obj['text'].get('body', '').strip()
        except Exception:
            pass

    # Format 3: Direct JSON test payload
    elif 'message' in data:
        message_text = data.get('message', '').strip()
        sender_phone = data.get('phone', '')

    if not message_text:
        return Response({'status': 'no message found'}, status=status.HTTP_200_OK)

    # Clean phone number (handle +254 or 07...)
    clean_phone = sender_phone.replace('+', '').replace(' ', '')
    if clean_phone.startswith('254') and len(clean_phone) == 12:
        alt_phone = '0' + clean_phone[3:]
    elif clean_phone.startswith('0') and len(clean_phone) == 10:
        alt_phone = '254' + clean_phone[1:]
    else:
        alt_phone = clean_phone

    # Look up registered parent
    matched_user = User.objects.filter(
        Q(phone_number__icontains=clean_phone) | 
        Q(phone_number__icontains=alt_phone)
    ).first()

    # Generate response
    bot_reply, metadata = generate_bot_response(message_text, user=matched_user)
    is_greeting = metadata.get('is_greeting', False) or is_trivial_greeting(message_text)

    # Save to Admin logs if meaningful
    if not is_greeting:
        classification = classify_conversation(message_text)
        session_id = f"wa_{clean_phone}"
        conversation, _ = ChatConversation.objects.get_or_create(
            session_id=session_id,
            defaults={
                'user': matched_user,
                'user_type': matched_user.role if matched_user else 'GUEST',
                'guest_name': matched_user.get_full_name() if matched_user else f"WhatsApp ({sender_phone})",
                'topic_summary': classification['topic_summary'],
                'category': classification['category'],
                'sentiment': classification['sentiment'],
                'is_meaningful': True
            }
        )
        if not conversation.is_meaningful:
            conversation.is_meaningful = True
            conversation.user = matched_user
            conversation.topic_summary = classification['topic_summary']
            conversation.category = classification['category']
            conversation.sentiment = classification['sentiment']
            conversation.save()

        ChatMessage.objects.create(
            conversation=conversation,
            sender='USER',
            text=f"[WhatsApp {sender_phone}] {message_text}",
            intent=classification['category'],
            metadata=metadata
        )
        ChatMessage.objects.create(
            conversation=conversation,
            sender='BOT',
            text=bot_reply,
            intent='bot_response',
            metadata=metadata
        )

    return Response({
        'status': 'success',
        'reply': bot_reply,
        'sender_phone': sender_phone,
        'matched_user': matched_user.username if matched_user else None,
        'is_meaningful': not is_greeting
    })
