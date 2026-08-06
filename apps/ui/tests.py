from django import forms
from django.template import Context, Template
from django.test import SimpleTestCase


class SampleForm(forms.Form):
    email = forms.EmailField(label="Email")
    comment = forms.CharField(label="Комментарий", widget=forms.Textarea, required=False)
    role = forms.ChoiceField(label="Роль", choices=[("a", "A")])
    agree = forms.BooleanField(label="Согласен")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("email") == "taken@example.test":
            raise forms.ValidationError("Этот адрес уже занят.")
        return cleaned


def render(template: str, **context) -> str:
    return Template("{% load form_tags %}" + template).render(Context(context))


class FormFieldTagTests(SimpleTestCase):
    def test_widget_gets_matching_component_class(self):
        form = SampleForm()

        html = render("{% form_field form.email %}", form=form)
        self.assertIn('class="ui-input"', html)

        html = render("{% form_field form.comment %}", form=form)
        self.assertIn('class="ui-textarea"', html)

        html = render("{% form_field form.role %}", form=form)
        self.assertIn('class="ui-select"', html)

    def test_checkbox_uses_choice_layout_without_control_class(self):
        html = render("{% form_field form.agree %}", form=SampleForm())

        self.assertIn("ui-check", html)
        self.assertNotIn('class="ui-input"', html)

    def test_optional_field_is_marked_for_the_reader(self):
        html = render("{% form_field form.comment %}", form=SampleForm())

        self.assertIn("необязательно", html)

    def test_invalid_field_is_announced_to_assistive_technology(self):
        form = SampleForm({"email": "not-an-email", "role": "a", "agree": True})
        form.is_valid()

        html = render("{% form_field form.email %}", form=form)

        # Без этой пары скринридер читает поле как обычное и не сообщает,
        # что именно с ним не так.
        self.assertIn('aria-invalid="true"', html)
        self.assertIn('aria-describedby="id_email-error"', html)
        self.assertIn('id="id_email-error"', html)
        self.assertIn("is-invalid", html)

    def test_valid_field_carries_no_error_markup(self):
        form = SampleForm({"email": "user@example.test", "role": "a", "agree": True})
        self.assertTrue(form.is_valid())

        html = render("{% form_field form.email %}", form=form)

        self.assertNotIn("aria-invalid", html)
        self.assertNotIn("ui-error", html)


class FormErrorsTagTests(SimpleTestCase):
    def test_unbound_form_renders_no_summary(self):
        html = render("{% form_errors form %}", form=SampleForm())

        self.assertNotIn("ui-error-summary", html)

    def test_valid_form_renders_no_summary(self):
        form = SampleForm({"email": "user@example.test", "role": "a", "agree": True})
        self.assertTrue(form.is_valid())

        html = render("{% form_errors form %}", form=form)

        self.assertNotIn("ui-error-summary", html)

    def test_summary_links_every_field_error_to_its_field(self):
        form = SampleForm({"email": "not-an-email", "role": "a"})
        form.is_valid()

        html = render("{% form_errors form %}", form=form)

        self.assertIn('role="alert"', html)
        self.assertIn('tabindex="-1"', html)
        self.assertIn('href="#id_email"', html)
        self.assertIn('href="#id_agree"', html)

    def test_summary_text_matches_field_text_exactly(self):
        """Правило GOV.UK: формулировки в сводке и у поля должны совпадать."""
        form = SampleForm({"email": "not-an-email", "role": "a", "agree": True})
        form.is_valid()

        summary = render("{% form_errors form %}", form=form)
        field = render("{% form_field form.email %}", form=form)
        message = form["email"].errors[0]

        self.assertIn(message, summary)
        self.assertIn(message, field)

    def test_non_field_error_appears_without_a_link(self):
        form = SampleForm({"email": "taken@example.test", "role": "a", "agree": True})
        form.is_valid()

        html = render("{% form_errors form %}", form=form)

        # Вести по такой ошибке некуда — ссылки быть не должно.
        self.assertIn("Этот адрес уже занят.", html)
        self.assertNotIn('href="#id___all__"', html)

    def test_custom_title_is_used(self):
        form = SampleForm({"role": "a"})
        form.is_valid()

        html = render('{% form_errors form "Не удалось войти" %}', form=form)

        self.assertIn("Не удалось войти", html)
