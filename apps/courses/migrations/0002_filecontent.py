from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("courses", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="FileContent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to="course_materials/")),
                ("description", models.TextField(blank=True)),
                ("content_block", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="file_content", to="courses.contentblock")),
            ],
        ),
    ]
