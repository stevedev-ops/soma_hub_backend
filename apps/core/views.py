from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from .models import User, Student
from apps.marketplace.models import TutorProfile

@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    data = request.data
    full_name = data.get('fullName', '').strip()
    phone = data.get('phone', '').strip()
    estate = data.get('estate', 'Kilimani, Nairobi').strip()
    role = data.get('role', 'parent').upper().strip()
    password = data.get('password', 'Pass1234!')
    bio = data.get('bio', '').strip()

    username = phone if phone else full_name.lower().replace(' ', '_')

    if User.objects.filter(username=username).exists():
        return Response({'error': f"An account with username/phone '{username}' already exists. Please sign in."}, status=status.HTTP_400_BAD_REQUEST)

    if phone and User.objects.filter(phone_number=phone).exists():
        return Response({'error': f"An account with phone number '{phone}' already exists. Please sign in."}, status=status.HTTP_400_BAD_REQUEST)

    name_parts = full_name.split(' ', 1)
    first_name = name_parts[0] if name_parts else 'User'
    last_name = name_parts[1] if len(name_parts) > 1 else ''

    user = User.objects.create_user(
        username=username,
        phone_number=phone,
        first_name=first_name,
        last_name=last_name,
        role=role if role in ['PARENT', 'STUDENT', 'TUTOR', 'CREATOR', 'ADMIN'] else 'PARENT',
        estate=estate,
        bio=bio
    )
    user.set_password(password)
    user.save()

    # If parent, create student
    children_data = []
    if user.role == 'PARENT':
        child_name = data.get('childName', '').strip()
        child_grade = data.get('childGrade', 'Grade 4 (CBC)')
        child_curriculum = data.get('childCurriculum', 'CBC')

        if child_name:
            c_parts = child_name.split(' ', 1)
            c_first = c_parts[0]
            c_last = c_parts[1] if len(c_parts) > 1 else (user.last_name or '')

            student = Student.objects.create(
                parent=user,
                first_name=c_first,
                last_name=c_last,
                grade_level=child_grade,
                curriculum_code=child_curriculum,
                avatar_url='https://images.unsplash.com/photo-1543332164-6e82f355badc?w=120'
            )
            children_data.append({
                'id': student.id,
                'name': f"{student.first_name} {student.last_name}".strip(),
                'grade': student.grade_level,
                'curriculum': student.curriculum_code,
                'avatar': student.avatar_url
            })

    if user.role == 'TUTOR':
        TutorProfile.objects.get_or_create(
            full_name=full_name or user.username,
            defaults={
                'title': data.get('title', 'Certified CBC & Cambridge Educator'),
                'bio': bio or 'Experienced homeschooling mentor in Kenya.',
                'avatar_url': 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=200',
                'hourly_rate_kes': data.get('hourlyRateKes', 1500),
                'estates_covered': [estate.split(',')[0]],
                'phone_contact': phone or '+254700000000'
            }
        )

    return Response({
        'success': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'name': f"{user.first_name} {user.last_name}".strip() if user.first_name else user.username,
            'role': user.role.lower(),
            'phone_number': user.phone_number or '',
            'estate': user.estate or 'Nairobi',
            'bio': user.bio,
            'avatar': 'https://images.unsplash.com/photo-1544717305-2782549b5136?w=150',
            'children': children_data
        }
    }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '').strip()

    if not username or not password:
        return Response({'error': 'Please provide both username/phone and password.'}, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(username=username, password=password)
    if not user:
        by_phone = User.objects.filter(phone_number=username).first()
        if by_phone and by_phone.check_password(password):
            user = by_phone

    if not user:
        return Response({'error': 'Invalid credentials. Please verify your phone/username and password.'}, status=status.HTTP_401_UNAUTHORIZED)

    children_data = []
    if user.role in ['PARENT', 'ADMIN', 'STUDENT']:
        children = Student.objects.filter(parent=user)
        children_data = [{
            'id': c.id,
            'name': f"{c.first_name} {c.last_name}".strip(),
            'grade': c.grade_level,
            'curriculum': c.curriculum_code,
            'avatar': c.avatar_url
        } for c in children]

    return Response({
        'success': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'name': f"{user.first_name} {user.last_name}".strip() if user.first_name else user.username,
            'role': user.role.lower(),
            'phone_number': user.phone_number or '',
            'estate': user.estate or 'Nairobi',
            'avatar': 'https://images.unsplash.com/photo-1544717305-2782549b5136?w=150',
            'children': children_data
        }
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def add_child_view(request):
    data = request.data
    user_id = data.get('parentId') or data.get('userId')
    phone = data.get('phone')

    parent = None
    if user_id:
        parent = User.objects.filter(id=user_id).first()
    if not parent and phone:
        parent = User.objects.filter(phone_number=phone).first()
    if not parent and request.user.is_authenticated:
        parent = request.user
    if not parent:
        parent = User.objects.filter(role='PARENT').first()

    child_name = data.get('name', '').strip() or data.get('childName', '').strip()
    if not child_name:
        return Response({'error': 'Child name is required.'}, status=status.HTTP_400_BAD_REQUEST)

    c_parts = child_name.split(' ', 1)
    c_first = c_parts[0]
    c_last = c_parts[1] if len(c_parts) > 1 else (parent.last_name if parent else '')

    student = Student.objects.create(
        parent=parent,
        first_name=c_first,
        last_name=c_last,
        grade_level=data.get('grade', 'Grade 4 (CBC)'),
        curriculum_code=data.get('curriculum', 'CBC'),
        avatar_url=data.get('avatar') or 'https://images.unsplash.com/photo-1543332164-6e82f355badc?w=120'
    )

    return Response({
        'success': True,
        'child': {
            'id': student.id,
            'name': f"{student.first_name} {student.last_name}".strip(),
            'grade': student.grade_level,
            'curriculum': student.curriculum_code,
            'avatar': student.avatar_url
        }
    }, status=status.HTTP_201_CREATED)

@api_view(['GET'])
def get_current_user(request):
    if request.user.is_authenticated:
        user = request.user
        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'name': f"{user.first_name} {user.last_name}".strip(),
                'role': user.role.lower(),
                'phone_number': user.phone_number,
                'estate': user.estate
            }
        })
    return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
