import django_filters
from django import forms
from django.db.models import Q

from stepper.models import StageEmployee, TemplateStep, ClearanceSheet


class StageEmployeeStudentFilter(django_filters.FilterSet):
    fio = django_filters.CharFilter(method='filter_by_fio', label="ФИО",
                                    widget=forms.TextInput(
                                        attrs={'class': 'form-control form-control-sm', 'placeholder': 'Асанов Асан'}))

    template_stage = django_filters.ModelChoiceFilter(
        queryset=TemplateStep.objects.filter(category=TemplateStep.STUDENT).select_related('stage'),
        label="Шаг",
        to_field_name="id",
        required=False,
        widget=forms.Select(attrs={'class': 'form-control form-control-sm'})
    )

    class Meta:
        model = StageEmployee
        fields = ['fio', 'template_stage']

    def filter_by_fio(self, queryset, name, value):
        parts = value.strip().split()

        filters = Q()
        for part in parts:
            filters |= (
                    Q(employee__first_name__icontains=part) |
                    Q(employee__last_name__icontains=part) |
                    Q(employee__fathers_name__icontains=part)
            )
        return queryset.filter(filters)


class CSFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method='filter_search', label='Поиск')

    class Meta:
        model = ClearanceSheet
        fields = ['search', ]

    def filter_search(self, queryset, name, value):
        query = Q(myedu_id__icontains=value) | Q(student_fio__icontains=value)
        if value.isdigit():
            query |= Q(id=int(value))
        return queryset.filter(query)
