from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("courses", "0002_filecontent")]

    operations = [
        migrations.CreateModel(
            name="CourseMaterialLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=255)),
                ("url", models.URLField()),
                ("description", models.TextField(blank=True)),
                ("position", models.PositiveIntegerField(default=1)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="material_links", to="courses.course")),
            ],
            options={"ordering": ["position", "created_at"]},
        )
    ]
