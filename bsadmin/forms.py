from django import forms
from django.forms import ClearableFileInput

from bsadmin.models import FacultyTranscript
from utils.pdf_compress import compress_pdf


class DateInput(forms.DateInput):
    input_type = 'date'


class LoginForm(forms.Form):
    email = forms.CharField(label='Логин',
                            widget=forms.TextInput(
                                attrs={
                                    "id": "email",
                                    "class": "form-control",
                                    "placeholder": 'введите логин',
                                    'required': True,
                                    "autofocus": "autofocus",

                                }
                            ))
    password = forms.CharField(label='Пароль',
                               widget=forms.PasswordInput(
                                   attrs={
                                       "id": "password",
                                       "class": "form-control",
                                       "placeholder": 'введите пароль',
                                       'required': True,
                                       "autocomplete": "on"
                                   }
                               ))


class FacultyTranscriptForm(forms.ModelForm):
    class Meta:
        model = FacultyTranscript
        fields = ['transcript_number']

        widgets = {
            'transcript_number': forms.TextInput(
                attrs={
                    "id": "transcript_number",
                    "class": "form-control form-control",
                    "placeholder": '123456789',
                    "autofocus": "autofocus",
                    "oninvalid": "this.setCustomValidity('Пожалуйста, заполните!')",
                    "oninput": "setCustomValidity('')"
                })

        }

    def clean_transcript_number(self):
        number = (self.cleaned_data.get('transcript_number') or '').replace(' ', '').strip()
        if not number:
            raise forms.ValidationError("Введите номер бланка.")
        duplicate = (FacultyTranscript.objects.filter(transcript_number=number)
                     .exclude(pk=self.instance.pk).select_related('faculty', 'category').first())
        if duplicate:
            raise forms.ValidationError(
                f"Бланк № {number} уже зарегистрирован: "
                f"{duplicate.faculty.short_name or duplicate.faculty.title}, категория {duplicate.category.title}.")
        return number


class CustomClearableFileInput(ClearableFileInput):
    template_name = "utils/_file.html"


class FailFacultyTranscriptForm(forms.ModelForm):
    MAX_FILE_SIZE = 3 * 1024 * 1024

    class Meta:
        model = FacultyTranscript
        fields = ['transcript_number', 'files']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['files'].required = True

    def clean_files(self):
        file = self.cleaned_data.get('files')
        if not file:
            return file
        if file.size > self.MAX_FILE_SIZE:
            raise forms.ValidationError("Размер файла не должен превышать 3 МБ.")
        # По стандарту заголовок «%PDF-» может стоять в пределах первых 1024 байт
        # (сканеры и конвертеры часто добавляют перед ним служебные байты).
        file.seek(0)
        head = file.read(1024)
        file.seek(0)
        if b"%PDF-" not in head:
            raise forms.ValidationError("Файл не похож на PDF. Сохраните скан в формате PDF и загрузите снова.")
        return compress_pdf(file)
