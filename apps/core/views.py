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
    """
    Self-Registration endpoint for Parents, Tutors, and Creators.
    Creates User and corresponding Student/TutorProfile in the database.
    """
    data = request.data
    full_name = data.get('fullName', '')
    phone = data.get('phone', '')
    estate = data.get('estate', 'Kilimani, Nairobi')
    role = data.get('role', 'parent').upper()
    password = data.get('password', 'Pass1234!')
    bio = data.get('bio', '')

    username = phone if phone else full_name.lower().replace(' ', '_') + str(User.objects.count())

    # Check existing user
    if User.objects.filter(username=username).exists() or (phone and User.objects.filter(phone_number=phone).exists()):
        user = User.objects.filter(username=username).first() or User.objects.filter(phone_number=phone).first()
    else:
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

    # If parent, create or update student
    children_data = []
    if user.role == 'PARENT':
        child_name = data.get('childName', '')
        child_grade = data.get('childGrade', 'Grade 4 (CBC)')
        child_curriculum = data.get('childCurriculum', 'CBC')

        if child_name:
            c_parts = child_name.split(' ', 1)
            c_first = c_parts[0]
            c_last = c_parts[1] if len(c_parts) > 1 else (user.last_name or 'Kariuki')

            student, created = Student.objects.get_or_create(
                parent=user,
                first_name=c_first,
                defaults={
                    'last_name': c_last,
                    'grade_level': child_grade,
                    'curriculum_code': child_curriculum,
                    'avatar_url': 'https://images.unsplash.com/photo-1543332164-6e82f355badc?w=120'
                }
            )

        students = Student.objects.filter(parent=user)
        children_data = [{
            'id': c.id,
            'name': f"{c.first_name} {c.last_name}",
            'grade': c.grade_level,
            'curriculum': c.curriculum_code,
            'avatar': c.avatar_url
        } for c in students]

    # If tutor, create TutorProfile
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
            'name': f"{user.first_name} {user.last_name}" if user.first_name else user.username,
            'role': user.role.lower(),
            'phone_number': user.phone_number or '+254712345678',
            'estate': user.estate or 'Kilimani, Nairobi',
            'bio': user.bio,
            'avatar': 'https://images.unsplash.com/photo-1544717305-2782549b5136?w=150',
            'children': children_data
        }
    }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    demo_role = request.data.get('demo_role')
    username = request.data.get('username')
    password = request.data.get('password')

    user = None

    if demo_role:
        if demo_role == 'parent':
            user = User.objects.filter(role='PARENT').first()
        elif demo_role == 'student':
            user = User.objects.filter(role='STUDENT').first()
        elif demo_role == 'tutor':
            user = User.objects.filter(role='TUTOR').first()
        elif demo_role == 'creator':
            user = User.objects.filter(role='CREATOR').first()
            if not user:
                user = User.objects.create(
                    username='mamateaches_creator',
                    first_name='Mama Liam',
                    last_name='(@MamaTeachesKenya)',
                    role='CREATOR',
                    phone_number='+254712345678',
                    estate='Kilimani, Nairobi',
                    bio='Homeschool mom of 2 in Nairobi. Simplifying Grade 4 CBC.'
                )
        elif demo_role == 'admin':
            user = User.objects.filter(role='ADMIN').first()
    elif username and password:
        user = authenticate(username=username, password=password)
        if not user:
            user = User.objects.filter(phone_number=username).first()
            if user and not user.check_password(password):
                user = None

    if not user:
        user = User.objects.first()

    if not user:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

    children_data = []
    if user.role in ['PARENT', 'ADMIN']:
        children = Student.objects.filter(parent=user)
        children_data = [{
            'id': c.id,
            'name': f"{c.first_name} {c.last_name}",
            'grade': c.grade_level,
            'curriculum': c.curriculum_code,
            'avatar': c.avatar_url
        } for c in children]

    return Response({
        'success': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'name': f"{user.first_name} {user.last_name}" if user.first_name else user.username,
            'role': user.role.lower(),
            'phone_number': user.phone_number or '+254712345678',
            'estate': user.estate or 'Kilimani, Nairobi',
            'avatar': 'https://images.unsplash.com/photo-1544717305-2782549b5136?w=150',
            'children': children_data
        }
    })

@api_view(['GET'])
def get_current_user(request):
    user = User.objects.first()
    return Response({
        'user': {
            'id': user.id,
            'username': user.username,
            'name': f"{user.first_name} {user.last_name}",
            'role': user.role.lower(),
            'phone_number': user.phone_number,
            'estate': user.estate
        }
    })
