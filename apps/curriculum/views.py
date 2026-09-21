import json
import os
import io
from django.db import transaction
from django.http import HttpResponse, JsonResponse, FileResponse
from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Curriculum, TermPackage, WeekModule, DailyLessonGuide
from .serializers import CurriculumSerializer, TermPackageSerializer, WeekModuleSerializer, DailyLessonGuideSerializer

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

class CurriculumViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Curriculum.objects.all()
    serializer_class = CurriculumSerializer

class TermPackageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TermPackage.objects.filter(is_active=True)
    serializer_class = TermPackageSerializer

@api_view(['GET'])
def get_package_detail(request, package_id):
    """Returns complete week-by-week structure and lessons for a given term package"""
    pkg = TermPackage.objects.filter(id=package_id).first()
    if not pkg:
        return Response({'error': 'Package not found'}, status=status.HTTP_404_NOT_FOUND)
    
    weeks = pkg.weeks.all().order_by('week_number')
    weeks_data = []
    for w in weeks:
        lessons = w.lessons.all().order_by('day_number')
        lessons_data = DailyLessonGuideSerializer(lessons, many=True).data
        weeks_data.append({
            'id': w.id,
            'week_number': w.week_number,
            'theme_title': w.theme_title,
            'printable_pack_title': w.printable_pack_title,
            'page_count': w.page_count,
            'learning_outcomes': w.learning_outcomes,
            'lessons': lessons_data
        })
    
    return Response({
        'id': pkg.id,
        'title': pkg.title,
        'subtitle': pkg.subtitle,
        'grade_level': pkg.grade_level,
        'curriculum_code': pkg.curriculum.code,
        'curriculum_name': pkg.curriculum.name,
        'price_kes': str(pkg.price_kes),
        'badge': pkg.badge,
        'features': pkg.features,
        'weeks': weeks_data
    })

@api_view(['GET'])
def download_package_json(request, package_id):
    """Exports full curriculum JSON for a specific package"""
    pkg = TermPackage.objects.filter(id=package_id).first()
    if not pkg:
        return Response({'error': 'Package not found'}, status=status.HTTP_404_NOT_FOUND)
    
    weeks_list = []
    for w in pkg.weeks.all().order_by('week_number'):
        lessons_list = []
        for l in w.lessons.all().order_by('day_number'):
            lessons_list.append({
                'day_number': l.day_number,
                'subject': l.subject,
                'time_slot': l.time_slot,
                'duration_minutes': l.duration_minutes,
                'topic': l.topic,
                'parent_script': l.parent_script,
                'learning_objective': l.learning_objective,
                'local_materials': l.local_materials,
                'step_by_step_activity': l.step_by_step_activity,
                'worksheet_name': l.worksheet_name,
                'is_lab_practical': l.is_lab_practical,
                'has_photo_submission': l.has_photo_submission
            })
        weeks_list.append({
            'week_number': w.week_number,
            'theme_title': w.theme_title,
            'printable_pack_title': w.printable_pack_title,
            'page_count': w.page_count,
            'learning_outcomes': w.learning_outcomes,
            'lessons': lessons_list
        })
        
    export_payload = {
        'curriculum': {
            'code': pkg.curriculum.code,
            'name': pkg.curriculum.name,
            'tagline': pkg.curriculum.tagline,
            'description': pkg.curriculum.description
        },
        'term_package': {
            'grade_level': pkg.grade_level,
            'term': pkg.term,
            'academic_year': pkg.academic_year,
            'title': pkg.title,
            'subtitle': pkg.subtitle,
            'price_kes': float(pkg.price_kes),
            'badge': pkg.badge,
            'features': pkg.features
        },
        'weeks': weeks_list
    }
    
    safe_name = pkg.title.replace(" ", "_").replace("/", "-")
    response = HttpResponse(
        json.dumps(export_payload, indent=2),
        content_type='application/json'
    )
    response['Content-Disposition'] = f'attachment; filename="{safe_name}_Curriculum.json"'
    return response

@api_view(['GET'])
def get_today_schedule(request):
    """Returns today's 3-hour lesson guides for the active package & week"""
    package_id = request.query_params.get('package_id')
    week_num = request.query_params.get('week', 3)
    day_num = request.query_params.get('day', 3)

    packages = TermPackage.objects.filter(is_active=True)
    if package_id:
        target_pkg = packages.filter(id=package_id).first()
    else:
        target_pkg = packages.first()

    if not target_pkg:
        return Response({'error': 'No active term package found'}, status=status.HTTP_404_NOT_FOUND)

    week = target_pkg.weeks.filter(week_number=week_num).first()
    if not week:
        week = target_pkg.weeks.first()

    if week:
        lessons_qs = week.lessons.filter(day_number=day_num)
        if not lessons_qs.exists():
            lessons = list(week.lessons.all()[:3])
        else:
            lessons = list(lessons_qs)
    else:
        lessons = []

    serializer = DailyLessonGuideSerializer(lessons, many=True)
    return Response({
        'package': {
            'id': target_pkg.id,
            'title': target_pkg.title,
            'grade_level': target_pkg.grade_level,
            'curriculum': target_pkg.curriculum.code,
        },
        'week': {
            'number': week.week_number if week else 1,
            'theme_title': week.theme_title if week else '',
            'printable_pack_title': week.printable_pack_title if week else '',
            'page_count': week.page_count if week else 10,
        },
        'day': int(day_num),
        'lessons': serializer.data
    })

@api_view(['POST'])
def import_curriculum_json(request):
    """
    Ingest a standardized Curriculum JSON file or payload into the system.
    Supports KICD CBC, British Cambridge, US Common Core, ACE, and Montessori.
    """
    try:
        if 'file' in request.FILES:
            file_obj = request.FILES['file']
            data = json.loads(file_obj.read().decode('utf-8'))
        else:
            data = request.data
            if isinstance(data, str):
                data = json.loads(data)

        # Validation
        for required_key in ['curriculum', 'term_package', 'weeks']:
            if required_key not in data:
                return Response(
                    {'error': f'Missing required key: "{required_key}" in curriculum JSON'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        curr_data = data['curriculum']
        pkg_data = data['term_package']
        weeks_data = data['weeks']

        with transaction.atomic():
            curriculum, _ = Curriculum.objects.update_or_create(
                code=curr_data['code'].upper().strip(),
                defaults={
                    'name': curr_data.get('name', curr_data['code']),
                    'tagline': curr_data.get('tagline', ''),
                    'description': curr_data.get('description', '')
                }
            )

            grade_level = pkg_data.get('grade_level', 'Grade 4')
            term_num = int(pkg_data.get('term', 1))
            academic_year = int(pkg_data.get('academic_year', 2026))

            term_pkg, _ = TermPackage.objects.update_or_create(
                curriculum=curriculum,
                grade_level=grade_level,
                term=term_num,
                academic_year=academic_year,
                defaults={
                    'title': pkg_data.get('title', f'{grade_level} Term {term_num}'),
                    'subtitle': pkg_data.get('subtitle', ''),
                    'price_kes': pkg_data.get('price_kes', 6500.00),
                    'badge': pkg_data.get('badge', 'Complete Homeschool-in-a-Box'),
                    'is_active': pkg_data.get('is_active', True),
                    'features': pkg_data.get('features', [])
                }
            )

            total_weeks = 0
            total_lessons = 0

            for w in weeks_data:
                w_num = int(w['week_number'])
                week_mod, _ = WeekModule.objects.update_or_create(
                    term_package=term_pkg,
                    week_number=w_num,
                    defaults={
                        'theme_title': w.get('theme_title', f'Week {w_num} Learning Module'),
                        'learning_outcomes': w.get('learning_outcomes', []),
                        'printable_pack_title': w.get('printable_pack_title', f'Week {w_num} Consolidated Printable Pack (PDF)'),
                        'page_count': w.get('page_count', 12)
                    }
                )
                total_weeks += 1

                for lesson in w.get('lessons', []):
                    day_num = int(lesson['day_number'])
                    subject = lesson.get('subject', 'General Learning')
                    DailyLessonGuide.objects.update_or_create(
                        week=week_mod,
                        day_number=day_num,
                        subject=subject,
                        defaults={
                            'time_slot': lesson.get('time_slot', '08:30 AM - 09:15 AM'),
                            'duration_minutes': lesson.get('duration_minutes', 45),
                            'topic': lesson.get('topic', f'{subject} Concept Exploration'),
                            'parent_script': lesson.get('parent_script', 'Begin by reading the lesson guide with your learner.'),
                            'learning_objective': lesson.get('learning_objective', 'Demonstrate conceptual mastery of the strand.'),
                            'local_materials': lesson.get('local_materials', []),
                            'step_by_step_activity': lesson.get('step_by_step_activity', 'Follow the activities in the printable pack.'),
                            'worksheet_name': lesson.get('worksheet_name', f'Worksheet #{w_num}.{day_num}'),
                            'is_lab_practical': lesson.get('is_lab_practical', False),
                            'has_photo_submission': lesson.get('has_photo_submission', False)
                        }
                    )
                    total_lessons += 1

            return Response({
                'success': True,
                'message': f'Successfully ingested {curriculum.name} ({term_pkg.title})',
                'curriculum': curriculum.code,
                'package_id': term_pkg.id,
                'package_title': term_pkg.title,
                'weeks_count': total_weeks,
                'lessons_count': total_lessons
            }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def get_curriculum_catalog_summary(request):
    """Returns all installed curricula with packages, weeks count, and total lessons count"""
    code_filter = request.query_params.get('curriculum')
    curricula = Curriculum.objects.all()
    if code_filter:
        curricula = curricula.filter(code__iexact=code_filter)
        
    summary = []
    for c in curricula:
        packages = c.packages.all().order_by('id')
        pkg_list = []
        total_lessons = 0
        total_weeks = 0
        for p in packages:
            weeks = p.weeks.all()
            w_count = weeks.count()
            l_count = DailyLessonGuide.objects.filter(week__in=weeks).count()
            total_weeks += w_count
            total_lessons += l_count
            pkg_list.append({
                'id': p.id,
                'grade_level': p.grade_level,
                'term': p.term,
                'title': p.title,
                'subtitle': p.subtitle,
                'badge': p.badge,
                'features': p.features,
                'weeks_count': w_count,
                'lessons_count': l_count,
                'price_kes': str(p.price_kes),
                'curriculum_code': c.code,
                'curriculum_name': c.name
            })
        summary.append({
            'code': c.code,
            'name': c.name,
            'tagline': c.tagline,
            'description': c.description,
            'packages': pkg_list,
            'total_weeks': total_weeks,
            'total_lessons': total_lessons
        })
    return Response({'curricula': summary})


from .models import CurriculumFramework, CreatorTemplate, AffiliateConversion, TeacherAvailabilitySlot

@api_view(['GET', 'POST'])
def frameworks_api(request):
    if request.method == 'GET':
        frameworks = CurriculumFramework.objects.filter(is_active=True).values('framework_id', 'name', 'organization', 'version', 'schema_json')
        return Response(list(frameworks))
    elif request.method == 'POST':
        data = request.data
        fw, created = CurriculumFramework.objects.update_or_create(
            framework_id=data.get('frameworkId') or data.get('framework_id'),
            defaults={
                'name': data.get('name', 'Custom Framework'),
                'organization': data.get('organization', 'Open Framework'),
                'version': data.get('version', '1.0'),
                'schema_json': data
            }
        )
        return Response({'success': True, 'framework_id': fw.framework_id}, status=status.HTTP_201_CREATED)

@api_view(['GET', 'POST'])
def creator_templates_api(request):
    if request.method == 'GET':
        templates = CreatorTemplate.objects.all().order_by('-created_at')
        res = [{
            'id': t.template_id,
            'creatorName': t.creator_name,
            'creatorHandle': t.creator_handle,
            'socialPlatform': t.social_platform,
            'creatorAvatar': t.creator_avatar,
            'creatorBio': t.creator_bio,
            'title': t.title,
            'curriculum': t.curriculum_code,
            'grade': t.grade_level,
            'tagline': t.tagline,
            'sampleWeekTheme': t.sample_week_theme,
            'highlights': t.highlights,
            'sampleLessons': t.sample_lessons,
            'importsCount': t.imports_count,
            'rating': float(t.rating),
            'affiliateCommissionKes': float(t.affiliate_commission_kes)
        } for t in templates]
        return Response(res)
    elif request.method == 'POST':
        d = request.data
        tpl = CreatorTemplate.objects.create(
            template_id=d.get('id', f"tpl_{Date.now()}"),
            creator_name=d.get('creatorName', 'Creator'),
            creator_handle=d.get('creatorHandle', '@creator'),
            social_platform=d.get('socialPlatform', 'TikTok & Instagram'),
            creator_avatar=d.get('creatorAvatar', ''),
            creator_bio=d.get('creatorBio', ''),
            title=d.get('title', 'Homeschool Routine'),
            curriculum_code=d.get('curriculum', 'CBC'),
            grade_level=d.get('grade', 'Grade 4'),
            tagline=d.get('tagline', ''),
            sample_week_theme=d.get('sampleWeekTheme', ''),
            highlights=d.get('highlights', []),
            sample_lessons=d.get('sampleLessons', [])
        )
        return Response({'success': True, 'template_id': tpl.template_id}, status=status.HTTP_201_CREATED)

@api_view(['GET', 'POST'])
def affiliate_conversions_api(request):
    if request.method == 'GET':
        conversions = AffiliateConversion.objects.all().order_by('-created_at')
        res = [{
            'id': f"conv_{c.id}",
            'creatorHandle': c.creator_handle,
            'parentName': c.parent_name,
            'commissionKes': float(c.commission_kes),
            'status': c.status,
            'date': c.created_at.strftime('%d-%b-%Y %H:%M')
        } for c in conversions]
        return Response(res)
    elif request.method == 'POST':
        d = request.data
        conv = AffiliateConversion.objects.create(
            creator_handle=d.get('creatorHandle', '@creator'),
            parent_name=d.get('parentName', 'Parent'),
            parent_phone=d.get('parentPhone', ''),
            template_id=d.get('templateId', ''),
            commission_kes=d.get('commissionKes', 1500),
            status='Credited'
        )
        return Response({'success': True, 'conversion_id': conv.id}, status=status.HTTP_201_CREATED)

@api_view(['GET', 'POST', 'DELETE'])
def teacher_slots_api(request, slot_id=None):
    if request.method == 'GET':
        slots = TeacherAvailabilitySlot.objects.all().order_by('day', 'start_time')
        res = [{
            'id': f"slot_{s.id}",
            'day': s.day,
            'startTime': s.start_time,
            'endTime': s.end_time,
            'title': s.title,
            'type': s.slot_type,
            'targetGroup': s.target_group,
            'maxLearners': s.max_learners,
            'bookedLearners': s.booked_learners,
            'hourlyRateKes': float(s.hourly_rate_kes),
            'status': s.status,
            'location': s.location,
            'liveLink': s.live_link
        } for s in slots]
        return Response(res)
    elif request.method == 'POST':
        d = request.data
        slot = TeacherAvailabilitySlot.objects.create(
            teacher_id=d.get('teacherId', 'mercy'),
            day=d.get('day', 'Monday'),
            start_time=d.get('startTime', '09:00 AM'),
            end_time=d.get('endTime', '11:00 AM'),
            title=d.get('title', 'Teaching Slot'),
            slot_type=d.get('type', 'pod'),
            target_group=d.get('targetGroup', 'Pod'),
            max_learners=d.get('maxLearners', 6),
            hourly_rate_kes=d.get('hourlyRateKes', 1500),
            status=d.get('status', 'Available'),
            location=d.get('location', 'Physical Pod & Virtual'),
            live_link=d.get('liveLink', 'https://meet.jit.si/somahome')
        )
        return Response({'success': True, 'slot_id': slot.id}, status=status.HTTP_201_CREATED)
    elif request.method == 'DELETE':
        if slot_id:
            TeacherAvailabilitySlot.objects.filter(id=slot_id).delete()
        return Response({'success': True})
