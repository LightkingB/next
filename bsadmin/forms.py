from django import forms
from django.forms import ClearableFileInput

from bsadmin.models import FacultyTranscript


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


class CustomClearableFileInput(ClearableFileInput):
    template_name = "utils/_file.html"


class FailFacultyTranscriptForm(forms.ModelForm):
    class Meta:
        model = FacultyTranscript
        fields = ['transcript_number', 'files']
