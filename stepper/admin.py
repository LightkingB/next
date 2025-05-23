from django.contrib import admin

from stepper.models import *


@admin.register(Stage)
class StageAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_mandatory')
    search_fields = ('name',)


@admin.register(TemplateStep)
class TemplateStepAdmin(admin.ModelAdmin):
    list_display = ('stage', 'category', 'order', 'role')
    list_filter = ('category',)
    list_editable = ('order', 'role',)


admin.site.register(EduYear)


@admin.register(StageEmployee)
class StageEmployeeAdmin(admin.ModelAdmin):
    list_display = ('get_employee_email', 'get_stage_name', 'is_active')
    search_fields = ('employee__email', 'employee__first_name', 'employee__last_name')
    list_filter = ('template_stage__stage__name',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('template_stage', 'template_stage__stage', 'employee')

    @admin.display(description="Название этапа")
    def get_stage_name(self, obj):
        return obj.template_stage.stage.name if obj.template_stage and obj.template_stage.stage else "-"

    @admin.display(description="Email")
    def get_employee_email(self, obj):
        return obj.employee.email if obj.employee else "-"


@admin.register(Diploma)
class DiplomaAdmin(admin.ModelAdmin):
    list_display = ('student', 'doc_number', 'reg_number', 'edu_year')
    search_fields = ('student',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('edu_year')


@admin.register(ClearanceSheet)
class TemplateStepAdmin(admin.ModelAdmin):
    list_display = ('student_fio', 'last_active')
    search_fields = ('student_fio',)
    list_filter = ('last_active',)


@admin.register(StageStatus)
class StageStatusAdmin(admin.ModelAdmin):
    list_display = ('trajectory', 'processed_by', 'comment_text', 'created_at')


@admin.register(Trajectory)
class TrajectoryAdmin(admin.ModelAdmin):
    list_display = ('clearance_sheet', 'get_stage_name', 'assigned_at', 'completed_at', 'assigned_by')
    search_fields = ('clearance_sheet__id', 'clearance_sheet__myedu_id', 'clearance_sheet__student_fio')
    list_filter = ('template_stage__stage__name',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('assigned_by', 'clearance_sheet', 'template_stage', 'template_stage__stage')

    @admin.display(description="Название этапа")
    def get_stage_name(self, obj):
        return obj.template_stage.stage.name if obj.template_stage and obj.template_stage.stage else "-"


@admin.register(Issuance)
class IssuanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'get_employee_email', 'doc_number', 'reg_number')
    search_fields = ('student', 'employee__email', 'employee__first_name', 'employee__last_name')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('employee')

    @admin.display(description="Email")
    def get_employee_email(self, obj):
        return obj.employee.email if obj.employee else "-"


admin.site.register(IssuanceHistory)
