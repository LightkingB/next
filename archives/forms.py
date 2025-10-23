from django import forms

from archives.models import Acts
from bsadmin.models import Faculty


class ActsForm(forms.ModelForm):
    class Meta:
        model = Acts
        fields = ('faculty', 'edu_form', 'notes', 'edu_year', 'category_form')
        widgets = {
            'notes': forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": '123456789',
                    "autofocus": "autofocus",
                    "oninvalid": "this.setCustomValidity('Пожалуйста, заполните!')",
                    "oninput": "setCustomValidity('')"
                }),
            'faculty': forms.Select(
                attrs={
                    "class": "form-control",
                    "placeholder": '123456789',
                    "autofocus": "autofocus",
                    "oninvalid": "this.setCustomValidity('Пожалуйста, заполните!')",
                    "oninput": "setCustomValidity('')"
                }),
            'edu_form': forms.Select(
                attrs={
                    "class": "form-control",
                    "placeholder": '123456789',
                    "autofocus": "autofocus",
                    "oninvalid": "this.setCustomValidity('Пожалуйста, заполните!')",
                    "oninput": "setCustomValidity('')"
                }),
            'edu_year': forms.Select(
                attrs={
                    "class": "form-control",
                    "placeholder": '123456789',
                    "autofocus": "autofocus",
                    "oninvalid": "this.setCustomValidity('Пожалуйста, заполните!')",
                    "oninput": "setCustomValidity('')"
                }),
            'category_form': forms.Select(
                attrs={
                    "class": "form-control",
                    "placeholder": '123456789',
                    "autofocus": "autofocus",
                    "oninvalid": "this.setCustomValidity('Пожалуйста, заполните!')",
                    "oninput": "setCustomValidity('')"
                }),
        }


class CustomFacultyForm(forms.ModelForm):
    class Meta:
        model = Faculty
        fields = ('title', 'short_name')
        widgets = {
            'title': forms.TextInput(
                attrs={
                    "class": "form-control",
                    "autofocus": "autofocus",
                    "oninvalid": "this.setCustomValidity('Пожалуйста, заполните!')",
                    "oninput": "setCustomValidity('')"
                }),
            'short_name': forms.TextInput(
                attrs={
                    "class": "form-control",
                    "autofocus": "autofocus",
                    "oninvalid": "this.setCustomValidity('Пожалуйста, заполните!')",
                    "oninput": "setCustomValidity('')"
                }),
        }
