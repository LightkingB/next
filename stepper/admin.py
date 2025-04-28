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
admin.site.register(StageEmployee)
admin.site.register(Diploma)
admin.site.register(ClearanceSheet)
admin.site.register(Trajectory)
admin.site.register(StageStatus)
admin.site.register(Issuance)
admin.site.register(IssuanceHistory)
