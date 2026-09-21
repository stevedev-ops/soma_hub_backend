from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from rest_framework.routers import DefaultRouter

from apps.curriculum.views import (
    CurriculumViewSet, TermPackageViewSet, get_today_schedule,
    import_curriculum_json, get_curriculum_catalog_summary,
    get_package_detail, download_package_json,
    frameworks_api, creator_templates_api, affiliate_conversions_api, teacher_slots_api
)
from apps.tracker.views import (
    EnrollmentViewSet, ProjectSubmissionViewSet, toggle_lesson_completion,
    get_report_card, download_report_card_pdf, download_printable_pack_pdf
)
from apps.marketplace.views import TutorViewSet, LearningPodViewSet
from apps.payments.views import initiate_stk_push, confirm_mpesa_pin
from apps.core.views import login_view, register_view, get_current_user, add_child_view

def health_check(request):
    return JsonResponse({
        'status': 'healthy',
        'service': 'SomaHome Kenya Homeschool API',
        'version': '2.0.0',
        'endpoints': {
            'curriculum': '/api/curriculum/trees/',
            'frameworks': '/api/curriculum/frameworks/',
            'daily_os': '/api/daily/today/',
            'auth': '/api/auth/login/',
            'payments': '/api/payments/stk-push/'
        }
    })

router = DefaultRouter()
router.register(r'curriculum/trees', CurriculumViewSet, basename='curriculum')
router.register(r'curriculum/packages', TermPackageViewSet, basename='packages')
router.register(r'tracker/enrollments', EnrollmentViewSet, basename='enrollments')
router.register(r'tracker/projects', ProjectSubmissionViewSet, basename='projects')
router.register(r'marketplace/tutors', TutorViewSet, basename='tutors')
router.register(r'marketplace/pods', LearningPodViewSet, basename='pods')

urlpatterns = [
    path('', health_check, name='root_health'),
    path('api/health/', health_check, name='api_health'),
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    
    # Auth & Self-Registration
    path('api/auth/register/', register_view, name='register'),
    path('api/auth/login/', login_view, name='login'),
    path('api/auth/me/', get_current_user, name='current_user'),
    path('api/parent/add-child/', add_child_view, name='add_child'),

    # Pluggable Curriculum Frameworks & Creator APIs
    path('api/curriculum/frameworks/', frameworks_api, name='frameworks_api'),
    path('api/creators/templates/', creator_templates_api, name='creator_templates_api'),
    path('api/creators/affiliates/', affiliate_conversions_api, name='affiliate_conversions_api'),
    path('api/tutors/schedule-slots/', teacher_slots_api, name='teacher_slots_api'),
    path('api/tutors/schedule-slots/<int:slot_id>/', teacher_slots_api, name='teacher_slot_delete'),

    # Curriculum Ingestion & Catalog & Direct Downloads
    path('api/curriculum/import-json/', import_curriculum_json, name='import_curriculum_json'),
    path('api/curriculum/catalog-summary/', get_curriculum_catalog_summary, name='curriculum_catalog_summary'),
    path('api/curriculum/packages/<int:package_id>/detail/', get_package_detail, name='package_detail'),
    path('api/curriculum/packages/<int:package_id>/download-json/', download_package_json, name='download_package_json'),

    # Custom Homeschool OS actions
    path('api/daily/today/', get_today_schedule, name='today_schedule'),
    path('api/daily/toggle-complete/', toggle_lesson_completion, name='toggle_complete'),
    path('api/reports/card/', get_report_card, name='report_card_default'),
    path('api/reports/card/<int:student_id>/', get_report_card, name='report_card'),

    # Real Binary PDF Downloads (ReportLab)
    path('api/reports/download-pdf/', download_report_card_pdf, name='download_report_default'),
    path('api/reports/download-pdf/<int:student_id>/', download_report_card_pdf, name='download_report'),
    path('api/curriculum/download-printable-pack/', download_printable_pack_pdf, name='download_pack_default'),
    path('api/curriculum/download-printable-pack/<int:week_id>/', download_printable_pack_pdf, name='download_pack'),
    
    # Safaricom M-Pesa Daraja
    path('api/payments/stk-push/', initiate_stk_push, name='stk_push'),
    path('api/payments/confirm-pin/', confirm_mpesa_pin, name='confirm_pin'),
]
