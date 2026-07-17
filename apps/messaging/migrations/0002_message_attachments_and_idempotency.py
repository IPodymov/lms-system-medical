import uuid

from django.db import migrations, models


def populate_client_tokens(apps, schema_editor):
    for model_name in ("DirectMessage", "CourseMessage"):
        model = apps.get_model("messaging", model_name)
        for item in model.objects.filter(client_token__isnull=True).iterator():
            item.client_token = uuid.uuid4()
            item.save(update_fields=["client_token"])


class Migration(migrations.Migration):
    dependencies = [("messaging", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="directmessage",
            name="body",
            field=models.TextField(blank=True, max_length=4000),
        ),
        migrations.AddField(
            model_name="directmessage",
            name="attachment",
            field=models.FileField(blank=True, upload_to="message_attachments/"),
        ),
        migrations.AddField(
            model_name="directmessage",
            name="attachment_content_type",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="directmessage",
            name="client_token",
            field=models.UUIDField(null=True),
        ),
        migrations.AlterField(
            model_name="coursemessage",
            name="body",
            field=models.TextField(blank=True, max_length=4000),
        ),
        migrations.AddField(
            model_name="coursemessage",
            name="attachment",
            field=models.FileField(blank=True, upload_to="message_attachments/"),
        ),
        migrations.AddField(
            model_name="coursemessage",
            name="attachment_content_type",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="coursemessage",
            name="client_token",
            field=models.UUIDField(null=True),
        ),
        migrations.RunPython(populate_client_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="directmessage",
            name="client_token",
            field=models.UUIDField(default=uuid.uuid4, unique=True),
        ),
        migrations.AlterField(
            model_name="coursemessage",
            name="client_token",
            field=models.UUIDField(default=uuid.uuid4, unique=True),
        ),
    ]
