from django import forms

from bsadmin.consts import STDEBT
from bsadmin.models import CustomUser, Role
from stepper.models import StageStatus, Issuance, TemplateStep, StageEmployee


class StudentTrajectoryForm(forms.Form):
    stages = forms.ModelMultipleChoiceField(
        queryset=TemplateStep.objects.filter(stage__is_mandatory=True, category=TemplateStep.STUDENT).select_related(
            'stage').order_by("order"),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Выберите этапы"
    )


class StageStatusForm(forms.ModelForm):
    class Meta:
        model = StageStatus
        fields = ('comment_text',)


class IssuanceForm(forms.ModelForm):
    class Meta:
        model = Issuance
        fields = (
            'doc_number', 'reg_number', 'files', 'signature', 'date_issue', 'fio', 'phone', 'inn', 'faculty',
            'speciality', 'note'
        )


class StageEmployeeForm(forms.ModelForm):
    class Meta:
        model = StageEmployee
        fields = ('template_stage', 'employee', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['employee'].queryset = CustomUser.objects.filter(is_worker=True).order_by('last_name', 'first_name')
        self.fields['template_stage'].queryset = TemplateStep.objects.filter(category=TemplateStep.STUDENT).order_by(
            'order')

    def clean(self):
        cleaned_data = super().clean()
        stage_employee = StageEmployee.objects.filter(employee=cleaned_data.get('employee'))

        if stage_employee and not self.instance.pk:
            self.add_error('employee', "Этот пользователь уже связан с этапом.")
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        role = instance.template_stage.role

        if role:
            if not instance.pk and instance.is_active:
                instance.employee.roles.add(role)
            elif instance.is_active:
                instance.employee.roles.add(role)
            else:
                instance.employee.roles.remove(role)
        if commit:
            instance.save()

        return instance
