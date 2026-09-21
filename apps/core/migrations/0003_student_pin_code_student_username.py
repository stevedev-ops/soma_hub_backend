from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_user_bio_alter_student_last_name_alter_user_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='pin_code',
            field=models.CharField(default='1234', max_length=10),
        ),
        migrations.AddField(
            model_name='student',
            name='username',
            field=models.CharField(blank=True, default='', max_length=60),
        ),
    ]
