from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.password_validation import validate_password
from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone

from apps.courses.models import CourseRun
from apps.imaging import resize_uploaded_image
from apps.organizations.models import Organization, OrganizationMembership

from .models import User

# Displayed at 58px (see .avatar-image); generous headroom for retina still
# cuts typical multi-MB phone photos down dramatically.
AVATAR_MAX_DIMENSION = 512


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

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        # Only a freshly uploaded file needs resizing — an unchanged existing
        # avatar comes back here as the already-stored FieldFile, and a
        # cleared avatar comes back as False.
        if isinstance(avatar, UploadedFile):
            return resize_uploaded_image(avatar, max_dimension=AVATAR_MAX_DIMENSION)
        return avatar


class UserPasswordForm(PasswordChangeForm):
    old_password = forms.CharField(label="Текущий пароль", widget=forms.PasswordInput)
    new_password1 = forms.CharField(label="Новый пароль", widget=forms.PasswordInput)
    new_password2 = forms.CharField(label="Повторите новый пароль", widget=forms.PasswordInput)


# ---------------------------------------------------------------------------
# Формы панели управления
#
# До этапа 4.10 все семь форм страницы управления читались во view напрямую
# из request.POST, а единственным способом сообщить об ошибке был
# messages.error поверх страницы: какое поле виновато, пользователь не знал
# и введённое терял целиком. Django Form даёт и то, и другое.
#
# Списки организаций, потоков и людей зависят от прав текущего пользователя,
# поэтому приходят в __init__ извне: форма не должна сама решать, что этому
# администратору видно.
# ---------------------------------------------------------------------------


class ManagementForm(forms.Form):
    """Общий предок форм страницы управления.

    На странице их семь, и у нескольких совпадают имена полей
    (organization, course_run, user). Django по умолчанию строит id как
    `id_<поле>`, поэтому в разметке появлялись повторяющиеся id: <label for>
    вёл в первую форму, и щелчок по метке фокусировал чужое поле. Префикс
    делает id уникальными, не трогая имена полей и, значит, обработчики.
    """

    id_prefix = "form"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("auto_id", f"{self.id_prefix}_%s")
        super().__init__(*args, **kwargs)
        # Стандартное «Обязательное поле» в сводке ошибок бесполезно: три
        # пустых поля дают три одинаковые строки, и по какой из них идти —
        # непонятно. Сообщение называет поле.
        for field in self.fields.values():
            if field.required:
                field.error_messages["required"] = f"Заполните поле «{field.label}»."


class OrganizationForm(ManagementForm, forms.ModelForm):
    id_prefix = "org"

    class Meta:
        model = Organization
        fields = ["name", "short_name", "institution_type"]
        labels = {
            "name": "Полное название",
            "short_name": "Сокращение",
            "institution_type": "Тип",
        }


class StudyGroupForm(ManagementForm):
    id_prefix = "group"

    organization = forms.ModelChoiceField(
        queryset=Organization.objects.none(), label="Организация", empty_label=None
    )
    name = forms.CharField(label="Номер группы", max_length=120)
    admission_year = forms.IntegerField(label="Поступление", min_value=2000)
    graduation_year = forms.IntegerField(label="Выпуск", min_value=2001)

    def __init__(self, *args, organizations=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["organization"].queryset = organizations
        # Прежний шаблон подставлял 2026 и 2030 литералами: через год
        # значения устарели бы молча. Считаем от текущего года, срок
        # обучения по умолчанию — четыре года.
        current_year = timezone.now().year
        self.fields["admission_year"].initial = current_year
        self.fields["graduation_year"].initial = current_year + 4

    def clean_name(self) -> str:
        return self.cleaned_data["name"].strip()

    def clean(self) -> dict:
        cleaned_data = super().clean()
        admission = cleaned_data.get("admission_year")
        graduation = cleaned_data.get("graduation_year")
        if admission and graduation and graduation <= admission:
            self.add_error("graduation_year", "Год выпуска должен быть больше года поступления.")
        return cleaned_data


class StudentImportForm(ManagementForm):
    id_prefix = "import"

    organization = forms.ModelChoiceField(
        queryset=Organization.objects.none(), label="Организация", empty_label=None
    )
    spreadsheet = forms.FileField(label="Excel-файл")

    def __init__(self, *args, organizations=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["organization"].queryset = organizations

    def clean_spreadsheet(self) -> UploadedFile:
        spreadsheet = self.cleaned_data["spreadsheet"]
        if not spreadsheet.name.lower().endswith(".xlsx"):
            raise forms.ValidationError("Файл должен быть в формате .xlsx.")
        return spreadsheet


class PersonFormMixin(ManagementForm):
    """Общая часть форм, создающих учётную запись.

    Пароль проверяется теми же валидаторами, что и при самостоятельной
    регистрации: администратор не должен иметь права выдать «12345».
    """

    def clean_email(self) -> str:
        return self.cleaned_data["email"].strip().lower()

    def clean_password(self) -> str:
        password = self.cleaned_data["password"]
        validate_password(password)
        return password


class ManagedUserForm(PersonFormMixin):
    id_prefix = "user"

    organization = forms.ModelChoiceField(
        queryset=Organization.objects.none(), label="Организация", empty_label=None
    )
    role = forms.ChoiceField(label="Роль", choices=())
    last_name = forms.CharField(label="Фамилия", max_length=150, required=False)
    first_name = forms.CharField(label="Имя", max_length=150, required=False)
    middle_name = forms.CharField(label="Отчество", max_length=150, required=False)
    username = forms.CharField(label="Логин", max_length=150)
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Временный пароль", strip=False, widget=forms.PasswordInput)

    def __init__(self, *args, organizations=None, roles=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["organization"].queryset = organizations
        self.fields["role"].choices = roles

    def clean_username(self) -> str:
        username = self.cleaned_data["username"].strip()
        email = self.data.get("email", "").strip().lower()
        if User.objects.exclude(email=email).filter(username__iexact=username).exists():
            raise forms.ValidationError("Это имя пользователя уже занято.")
        return username


class GroupStudentForm(PersonFormMixin):
    id_prefix = "student"

    """Создание студента прямо в составе учебной группы."""

    last_name = forms.CharField(label="Фамилия", max_length=150)
    first_name = forms.CharField(label="Имя", max_length=150)
    middle_name = forms.CharField(label="Отчество", max_length=150, required=False)
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Временный пароль", strip=False, widget=forms.PasswordInput)
    student_number = forms.CharField(label="Номер студента", max_length=50, required=False)


class CourseStaffForm(ManagementForm):
    id_prefix = "staff"

    course_run = forms.ModelChoiceField(
        queryset=CourseRun.objects.none(), label="Поток", empty_label=None
    )
    user = forms.ModelChoiceField(
        queryset=User.objects.none(), label="Преподаватель", empty_label=None
    )
    role = forms.ChoiceField(
        label="Роль",
        choices=[("curator", "Куратор"), ("teacher", "Преподаватель"), ("assistant", "Ассистент")],
    )

    def __init__(self, *args, course_runs=None, teachers=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["course_run"].queryset = course_runs
        self.fields["user"].queryset = teachers

    def clean(self) -> dict:
        cleaned_data = super().clean()
        course_run = cleaned_data.get("course_run")
        user = cleaned_data.get("user")
        if course_run and user:
            has_teacher_role = OrganizationMembership.objects.filter(
                user=user,
                organization=course_run.course.organization,
                role=OrganizationMembership.Role.TEACHER,
                status="active",
            ).exists()
            if not has_teacher_role:
                self.add_error("user", "Этот преподаватель не работает в организации курса.")
        return cleaned_data


class CourseEnrollmentForm(ManagementForm):
    id_prefix = "enroll"

    course_run = forms.ModelChoiceField(
        queryset=CourseRun.objects.none(), label="Поток", empty_label=None
    )
    user = forms.ModelChoiceField(queryset=User.objects.none(), label="Студент", empty_label=None)

    def __init__(self, *args, course_runs=None, students=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["course_run"].queryset = course_runs
        self.fields["user"].queryset = students

    def clean(self) -> dict:
        cleaned_data = super().clean()
        course_run = cleaned_data.get("course_run")
        user = cleaned_data.get("user")
        if course_run and user:
            is_student = OrganizationMembership.objects.filter(
                user=user,
                organization=course_run.course.organization,
                role=OrganizationMembership.Role.STUDENT,
                status="active",
            ).exists()
            if not is_student:
                self.add_error("user", "Этот слушатель не числится в организации курса.")
        return cleaned_data


class EnrollmentLinkForm(ManagementForm):
    id_prefix = "link"

    course_run = forms.ModelChoiceField(
        queryset=CourseRun.objects.none(), label="Поток", empty_label=None
    )
    label = forms.CharField(label="Название для команды", max_length=120, required=False)
    expires_at = forms.DateTimeField(label="Действует до", required=False)

    def __init__(self, *args, course_runs=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["course_run"].queryset = course_runs

    def clean_expires_at(self):
        expires_at = self.cleaned_data["expires_at"]
        # Поле <input type="datetime-local"> присылает время без пояса.
        if expires_at and timezone.is_naive(expires_at):
            return timezone.make_aware(expires_at)
        return expires_at
