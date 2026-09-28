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
    message_text = request.data.get('message', '').strip()
    session_id = request.data.get('session_id') or str(uuid.uuid4())
    guest_name = request.data.get('guest_name', 'Guest Visitor')

    if not message_text:
        return Response({'error': 'Message text is required'}, status=status.HTTP_400_BAD_REQUEST)

    bot_reply, metadata = generate_bot_response(message_text, user=None)
    is_greeting = metadata.get('is_greeting', False) or is_trivial_greeting(message_text)

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
        'user_type': 'GUEST'
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def chatbot_authenticated_view(request):
    message_text = request.data.get('message', '').strip()
    session_id = request.data.get('session_id') or str(uuid.uuid4())
    student_id = request.data.get('student_id')
    user_email = request.data.get('user_email')
    user_name = request.data.get('user_name')
    user_role = request.data.get('user_role', 'PARENT')

    if not message_text:
        return Response({'error': 'Message text is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Determine user
    user = None
    if request.user and request.user.is_authenticated:
        user = request.user
    elif user_email:
        user = User.objects.filter(
            Q(email__iexact=user_email) | Q(username__iexact=user_email) | Q(phone_number__iexact=user_email)
        ).first()

    if not user and (user_email or user_name):
        # Create lightweight session proxy for demo / logged-in user
        user = User(
            username=user_name or user_email or 'Parent User',
            first_name=user_name or 'Parent',
            email=user_email or 'parent@somahome.ke',
            role=user_role
        )

    student = None
    if student_id:
        if isinstance(student_id, int) or (isinstance(student_id, str) and student_id.isdigit()):
            student = Student.objects.filter(id=int(student_id)).first()
        elif isinstance(student_id, str):
            student = Student.objects.filter(
                Q(first_name__iexact=student_id) | Q(username__iexact=student_id)
            ).first()

    if not student and user:
        if user.id:
            student = Student.objects.filter(parent=user).first()
        if not student:
            student = Student(first_name="Liam", last_name="Kariuki", grade_level="Grade 4", curriculum_code="CBC")

    bot_reply, metadata = generate_bot_response(message_text, user=user, student=student)
    is_greeting = metadata.get('is_greeting', False) or is_trivial_greeting(message_text)

    if not is_greeting:
        classification = classify_conversation(message_text)
        assigned_role = user.role if user else 'PARENT'
        
        conversation, _ = ChatConversation.objects.get_or_create(
            session_id=session_id,
            defaults={
                'user': user if user and user.id else None,
                'student': student if student and student.id else None,
                'user_type': assigned_role,
                'guest_name': user.get_full_name() if (user and hasattr(user, 'get_full_name') and user.get_full_name()) else (user_name or 'Parent / Learner'),
                'topic_summary': classification['topic_summary'],
                'category': classification['category'],
                'sentiment': classification['sentiment'],
                'is_meaningful': True
            }
        )
        if not conversation.is_meaningful:
            conversation.is_meaningful = True
            if user and user.id:
                conversation.user = user
            if student and student.id:
                conversation.student = student
            conversation.user_type = assigned_role
            conversation.topic_summary = classification['topic_summary']
            conversation.category = classification['category']
            conversation.sentiment = classification['sentiment']
            conversation.save()

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
        'user_type': user.role if user else 'PARENT'
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def admin_chat_logs_view(request):
    search_q = request.GET.get('search', '').strip()
    category_filter = request.GET.get('category', '').strip()
    sentiment_filter = request.GET.get('sentiment', '').strip()

    convs = ChatConversation.objects.filter(is_meaningful=True).order_by('-updated_at')

    if search_q:
        convs = convs.filter(
            Q(topic_summary__icontains=search_q) |
            Q(guest_name__icontains=search_q) |
            Q(user__username__icontains=search_q) |
            Q(admin_tags__icontains=search_q) |
            Q(messages__text__icontains=search_q)
        ).distinct()

    if category_filter and category_filter != 'ALL':
        convs = convs.filter(category=category_filter)

    if sentiment_filter and sentiment_filter != 'ALL':
        convs = convs.filter(sentiment=sentiment_filter)

    total_count = convs.count()
    convs_page = convs[:50]

    data = []
    for c in convs_page:
        msgs = list(c.messages.order_by('created_at').values('id', 'sender', 'text', 'created_at', 'intent'))
        user_display = c.guest_name
        if c.user:
            user_display = c.user.get_full_name() or c.user.username

        data.append({
            'id': c.id,
            'session_id': c.session_id,
            'user_type': c.user_type,
            'user_display': user_display,
            'category': c.category,
            'sentiment': c.sentiment,
            'topic_summary': c.topic_summary,
            'admin_notes': c.admin_notes,
            'admin_tags': c.admin_tags,
            'is_resolved': c.is_resolved,
            'created_at': c.created_at.isoformat(),
            'updated_at': c.updated_at.isoformat(),
            'message_count': len(msgs),
            'messages': [
                {
                    'id': m['id'],
                    'sender': m['sender'],
                    'text': m['text'],
                    'created_at': m['created_at'].isoformat(),
                    'intent': m['intent']
                }
                for m in msgs
            ]
        })

    return Response({'total': total_count, 'conversations': data})


@api_view(['PATCH'])
@permission_classes([AllowAny])
def admin_update_conversation_view(request, conv_id):
    conv = ChatConversation.objects.filter(id=conv_id).first()
    if not conv:
        return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)

    if 'admin_notes' in request.data:
        conv.admin_notes = request.data['admin_notes']
    if 'admin_tags' in request.data:
        conv.admin_tags = request.data['admin_tags']
    if 'is_resolved' in request.data:
        conv.is_resolved = bool(request.data['is_resolved'])
    if 'category' in request.data:
        conv.category = request.data['category']
    if 'sentiment' in request.data:
        conv.sentiment = request.data['sentiment']

    conv.save()
    return Response({'status': 'success', 'id': conv.id})


@api_view(['GET'])
@permission_classes([AllowAny])
def admin_chat_analytics_view(request):
    meaningful = ChatConversation.objects.filter(is_meaningful=True)
    total_chats = meaningful.count()
    
    cat_counts = meaningful.values('category').annotate(count=Count('id')).order_by('-count')
    sent_counts = meaningful.values('sentiment').annotate(count=Count('id')).order_by('-count')
    
    total_messages = ChatMessage.objects.filter(conversation__is_meaningful=True).count()
    avg_per_conv = round((total_messages / total_chats), 1) if total_chats > 0 else 0

    return Response({
        'total_conversations': total_chats,
        'total_messages': total_messages,
        'avg_messages_per_chat': avg_per_conv,
        'category_breakdown': list(cat_counts),
        'sentiment_breakdown': list(sent_counts)
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def whatsapp_webhook_view(request):
    from_number = request.data.get('From') or request.data.get('from')
    body_text = request.data.get('Body') or request.data.get('text', {}).get('body') or request.data.get('message', '')

    if not body_text:
        return Response({'status': 'ignored', 'reason': 'no message body'})

    session_id = f"wa_{from_number}_{date.today().isoformat()}"
    bot_reply, metadata = generate_bot_response(body_text, user=None)

    return Response({
        'status': 'success',
        'reply': bot_reply,
        'to': from_number
    })
