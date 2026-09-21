import os
import json
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.curriculum.models import Curriculum, TermPackage, WeekModule, DailyLessonGuide

class Command(BaseCommand):
    help = 'Import and ingest full curriculum syllabi from a standardized JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            required=True,
            help='Path to the curriculum JSON file (e.g. curriculum_templates/kicd_grade4_cbc_term1.json)'
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Overwrite existing packages and lesson guides if already present'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        overwrite = options['overwrite']

        if not os.path.exists(file_path):
            raise CommandError(f'Curriculum file "{file_path}" does not exist.')

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            raise CommandError(f'Failed to parse JSON file: {e}')

        # Validation
        for required_key in ['curriculum', 'term_package', 'weeks']:
            if required_key not in data:
                raise CommandError(f'Invalid curriculum JSON schema. Missing top-level key: "{required_key}"')

        curr_data = data['curriculum']
        pkg_data = data['term_package']
        weeks_data = data['weeks']

        self.stdout.write(self.style.NOTICE(f"Initiating curriculum ingestion: {curr_data.get('name')} ({curr_data.get('code')})"))

        with transaction.atomic():
            # 1. Ingest Curriculum
            curriculum, curr_created = Curriculum.objects.update_or_create(
                code=curr_data['code'].upper().strip(),
                defaults={
                    'name': curr_data.get('name', curr_data['code']),
                    'tagline': curr_data.get('tagline', ''),
                    'description': curr_data.get('description', '')
                }
            )
            curr_action = "Created" if curr_created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"  ✓ {curr_action} Curriculum: {curriculum.name} [{curriculum.code}]"))

            # 2. Ingest Term Package
            grade_level = pkg_data.get('grade_level', 'Grade 4')
            term_num = int(pkg_data.get('term', 1))
            academic_year = int(pkg_data.get('academic_year', 2026))

            term_pkg, pkg_created = TermPackage.objects.update_or_create(
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
            pkg_action = "Created" if pkg_created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"  ✓ {pkg_action} Term Package: {term_pkg.title} (KES {term_pkg.price_kes})"))

            # 3. Ingest Weeks and Daily Lessons
            total_weeks_ingested = 0
            total_lessons_ingested = 0

            for w in weeks_data:
                w_num = int(w['week_number'])
                week_mod, w_created = WeekModule.objects.update_or_create(
                    term_package=term_pkg,
                    week_number=w_num,
                    defaults={
                        'theme_title': w.get('theme_title', f'Week {w_num} Learning Module'),
                        'learning_outcomes': w.get('learning_outcomes', []),
                        'printable_pack_title': w.get('printable_pack_title', f'Week {w_num} Consolidated Printable Pack (PDF)'),
                        'page_count': w.get('page_count', 12)
                    }
                )
                total_weeks_ingested += 1

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
                    total_lessons_ingested += 1

        self.stdout.write(self.style.SUCCESS(
            f"\n🎉 Curriculum Ingestion Complete!\n"
            f"   - Curriculum: {curriculum.name} [{curriculum.code}]\n"
            f"   - Term Package: {term_pkg.title}\n"
            f"   - Weeks Ingested: {total_weeks_ingested}\n"
            f"   - Daily Guides Ingested: {total_lessons_ingested}\n"
            f"   - Ready for Instant Homeschool OS & Printable Pack Generation!"
        ))
