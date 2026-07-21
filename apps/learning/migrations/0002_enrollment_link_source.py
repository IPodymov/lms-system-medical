from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("learning", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="enrollment",
            name="enrollment_source",
            field=models.CharField(
                choices=[
                    ("manual", "Вручную"),
                    ("self", "Самозапись"),
                    ("group", "Группа"),
                    ("link", "По ссылке"),
                ],
                default="self",
                max_length=12,
            ),
        )
    ]