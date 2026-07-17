import uuid

from django import forms

from .models import CourseMessage, DirectMessage


class MessageForm(forms.ModelForm):
    """Shared validation for a message text and its optional local attachment."""

    client_token = forms.UUIDField(widget=forms.HiddenInput, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["client_token"].initial = uuid.uuid4()

    def clean(self):
        cleaned_data = super().clean() or {}
        if not cleaned_data.get("client_token"):
            cleaned_data["client_token"] = uuid.uuid4()
        if not cleaned_data.get("body", "").strip() and not cleaned_data.get("attachment"):
            raise forms.ValidationError("Введите сообщение или прикрепите файл.")
        return cleaned_data

    def clean_attachment(self):
        attachment = self.cleaned_data.get("attachment")
        if attachment and attachment.size > 10 * 1024 * 1024:
            raise forms.ValidationError("Размер вложения не должен превышать 10 МБ.")
        return attachment


class DirectMessageForm(MessageForm):
    class Meta:
        model = DirectMessage
        fields = ["body", "attachment", "client_token"]
        labels = {"body": "Сообщение"}
        widgets = {"body": forms.Textarea(attrs={"rows": 3, "placeholder": "Напишите сообщение…"})}


class CourseMessageForm(MessageForm):
    class Meta:
        model = CourseMessage
        fields = ["body", "attachment", "client_token"]
        labels = {"body": "Сообщение в общий чат"}
        widgets = {
            "body": forms.Textarea(attrs={"rows": 3, "placeholder": "Задайте вопрос группе…"})
        }
