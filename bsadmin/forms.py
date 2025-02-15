from django import forms

from bsadmin.models import AcademicTranscript, FacultyTranscript


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


class AcademicTranscriptForm(forms.ModelForm):
    class Meta:
        model = AcademicTranscript
        fields = ['title', 'count']

        widgets = {
            'title': forms.TextInput(
                attrs={
                    "id": "title",
                    "class": "form-control form-control-sm",
                    "placeholder": 'Название',
                    "autofocus": "autofocus",
                    "oninvalid": "this.setCustomValidity('Пожалуйста, заполните!')",
                    "oninput": "setCustomValidity('')"
                }),
            'count': forms.NumberInput(
                attrs={
                    "id": "count",
                    "class": "form-control form-control-sm",
                    "placeholder": 'Количество',
                    "autofocus": "autofocus",
                    "oninvalid": "this.setCustomValidity('Пожалуйста, заполните!')",
                    "oninput": "setCustomValidity('')"
                })
        }


class FacultyTranscriptForm(forms.ModelForm):
    class Meta:
        model = FacultyTranscript
        fields = ['transcript_number', 'category']

        widgets = {
            'transcript_number': forms.TextInput(
                attrs={
                    "id": "transcript_number",
                    "class": "form-control form-control",
                    "placeholder": '123456789',
                    "autofocus": "autofocus",
                    "oninvalid": "this.setCustomValidity('Пожалуйста, заполните!')",
                    "oninput": "setCustomValidity('')"
                }),
            'category': forms.Select(
                attrs={
                    "id": "category",
                    "class": "form-control form-control",
                    "autofocus": "autofocus",
                    "oninvalid": "this.setCustomValidity('Пожалуйста, заполните!')",
                    "oninput": "setCustomValidity('')"
                })

        }
