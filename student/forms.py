from django import forms
from django.core.exceptions import ValidationError

from stepper.models import EduYear
from student.choices import QuestionType
from student.consts import (
    SURVEY_OPTION_TEXT_MAX,
    SURVEY_OPTION_TEXT_MIN,
    SURVEY_OPTIONS_MAX,
    SURVEY_OPTIONS_MIN,
    SURVEY_QUESTION_TEXT_MAX,
    SURVEY_QUESTION_TEXT_MIN,
)
from student.models import StudentProfile, Survey, SurveyOption, SurveyQuestion, validate_work_phone


class StudentPhoneForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ("work_phone",)
        widgets = {
            "work_phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "+996 XXX XX XX XX",
                }
            ),
        }
        labels = {
            "work_phone": "Рабочий номер телефона",
        }

    def clean_work_phone(self):
        phone = self.cleaned_data.get("work_phone", "")
        validate_work_phone(phone)
        return phone.strip()


class SurveyForm(forms.ModelForm):
    class Meta:
        model = Survey
        fields = ("title", "description", "is_active")
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control survey-input", "placeholder": "Название анкеты"}
            ),
            "description": forms.Textarea(
                attrs={"class": "form-control survey-input", "rows": 3, "placeholder": "Краткое описание (необязательно)"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "custom-control-input"}),
        }

    def clean_title(self):
        title = self.cleaned_data.get("title", "").strip()
        if len(title) < 3:
            raise forms.ValidationError("Название должно содержать минимум 3 символа.")
        if len(title) > 255:
            raise forms.ValidationError("Название не должно превышать 255 символов.")
        return title


class SurveyQuestionModalForm(forms.Form):
    text = forms.CharField(
        label="Текст вопроса",
        min_length=SURVEY_QUESTION_TEXT_MIN,
        max_length=SURVEY_QUESTION_TEXT_MAX,
        widget=forms.Textarea(
            attrs={
                "class": "form-control survey-input",
                "rows": 3,
                "placeholder": "Введите текст вопроса",
            }
        ),
    )
    question_type = forms.ChoiceField(
        label="Тип ответа",
        choices=QuestionType.choices,
        widget=forms.Select(attrs={"class": "form-control survey-input"}),
    )

    def __init__(self, *args, **kwargs):
        self._options_initial = kwargs.pop("options_initial", None)
        super().__init__(*args, **kwargs)

    def get_options_for_display(self):
        if self.is_bound:
            values = self.data.getlist("options")
            if values:
                return values
        if self._options_initial:
            return list(self._options_initial)
        return ["", ""]

    def clean(self):
        cleaned_data = super().clean()
        raw_options = self.data.getlist("options") if hasattr(self.data, "getlist") else []
        options = [value.strip() for value in raw_options if value and value.strip()]

        if len(options) < SURVEY_OPTIONS_MIN:
            raise ValidationError(
                f"Добавьте минимум {SURVEY_OPTIONS_MIN} варианта ответа."
            )
        if len(options) > SURVEY_OPTIONS_MAX:
            raise ValidationError(
                f"Максимум {SURVEY_OPTIONS_MAX} вариантов ответа."
            )

        lowered = [option.lower() for option in options]
        if len(lowered) != len(set(lowered)):
            raise ValidationError("Варианты ответа не должны повторяться.")

        for index, option in enumerate(options, start=1):
            if len(option) < SURVEY_OPTION_TEXT_MIN:
                raise ValidationError(f"Вариант {index}: текст не может быть пустым.")
            if len(option) > SURVEY_OPTION_TEXT_MAX:
                raise ValidationError(
                    f"Вариант {index}: не более {SURVEY_OPTION_TEXT_MAX} символов."
                )

        cleaned_data["options"] = options
        return cleaned_data

    @classmethod
    def from_question(cls, question):
        options = list(question.options.order_by("order").values_list("text", flat=True))
        if len(options) < SURVEY_OPTIONS_MIN:
            options.extend([""] * (SURVEY_OPTIONS_MIN - len(options)))
        return cls(
            initial={
                "text": question.text,
                "question_type": question.question_type,
            },
            options_initial=options,
        )


class SurveyDeleteForm(forms.Form):
    confirm = forms.BooleanField(label="Подтвердить удаление", required=True)


class SurveySubmissionFilterForm(forms.Form):
    edu_year = forms.ModelChoiceField(
        label="Учебный год",
        queryset=EduYear.objects.none(),
        required=False,
        empty_label="Все",
        widget=forms.Select(attrs={"class": "form-control form-control-sm survey-input"}),
    )
    date_from = forms.DateField(
        label="Дата с",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm survey-input"}),
    )
    date_to = forms.DateField(
        label="Дата по",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm survey-input"}),
    )
    group = forms.CharField(
        label="Группа",
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control form-control-sm survey-input", "placeholder": "Все группы", "list": "survey-group-list"}
        ),
    )
    search = forms.CharField(
        label="ФИО или логин",
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control form-control-sm survey-input", "placeholder": "Поиск…"}
        ),
    )

    def __init__(self, survey, *args, edu_years=None, **kwargs):
        self.survey = survey
        super().__init__(*args, **kwargs)
        if edu_years is not None:
            self.fields["edu_year"].queryset = edu_years
        else:
            self.fields["edu_year"].queryset = (
                EduYear.objects.filter(survey_submissions__survey=survey)
                .distinct()
                .order_by("-title")
            )

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get("date_from")
        date_to = cleaned_data.get("date_to")
        if date_from and date_to and date_from > date_to:
            raise ValidationError("Дата «с» не может быть позже даты «по».")
        return cleaned_data


def build_survey_form(survey):
    class DynamicSurveyForm(forms.Form):
        pass

    for question in survey.questions.all():
        options = [(str(option.id), option.text) for option in question.options.all()]
        if question.question_type == QuestionType.RADIO:
            DynamicSurveyForm.base_fields[f"q_{question.id}"] = forms.ChoiceField(
                label=question.text,
                choices=options,
                widget=forms.RadioSelect,
                required=True,
            )
        else:
            DynamicSurveyForm.base_fields[f"q_{question.id}"] = forms.MultipleChoiceField(
                label=question.text,
                choices=options,
                widget=forms.CheckboxSelectMultiple,
                required=True,
            )

    return DynamicSurveyForm
