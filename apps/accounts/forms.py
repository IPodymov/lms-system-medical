from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.password_validation import validate_password

from .models import User


class RegistrationForm(forms.ModelForm):
    password1 = forms.CharField(label="Пароль", strip=False, widget=forms.PasswordInput)
    password2 = forms.CharField(
        label="Повторите пароль",
        strip=False,
        widget=forms.PasswordInput,
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        labels = {
            "first_name": "Имя",
            "last_name": "Фамилия",
            "email": "Email",
        }

    def clean_email(self) -> str:
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Пользователь с таким email уже зарегистрирован.")
        return email

    def clean_password2(self) -> str:
        password = self.cleaned_data.get("password1")
        confirmation = self.cleaned_data["password2"]
        if password != confirmation:
            raise forms.ValidationError("Пароли не совпадают.")
        validate_password(confirmation, self.instance)
        return confirmation

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.username = user.email
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    """Editable contact and visual identity fields for the signed-in user."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "middle_name", "username", "email", "avatar"]
        labels = {
            "first_name": "Имя",
            "last_name": "Фамилия",
            "middle_name": "Отчество",
            "username": "Имя пользователя",
            "email": "Email",
            "avatar": "Аватар",
        }

    def clean_email(self) -> str:
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.exclude(pk=self.instance.pk).filter(email__iexact=email).exists():
            raise forms.ValidationError("Этот email уже используется.")
        return email

    def clean_username(self) -> str:
        username = self.cleaned_data["username"].strip()
        if not username:
            raise forms.ValidationError("Укажите имя пользователя.")
        if User.objects.exclude(pk=self.instance.pk).filter(username__iexact=username).exists():
            raise forms.ValidationError("Это имя пользователя уже занято.")
        return username


class UserPasswordForm(PasswordChangeForm):
    old_password = forms.CharField(label="Текущий пароль", widget=forms.PasswordInput)
    new_password1 = forms.CharField(label="Новый пароль", widget=forms.PasswordInput)
    new_password2 = forms.CharField(label="Повторите новый пароль", widget=forms.PasswordInput)
