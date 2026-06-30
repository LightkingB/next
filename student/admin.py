from django.contrib import admin

from student.models import (
    StudentProfile,
    Survey,
    SurveyAnswerItem,
    SurveyOption,
    SurveyQuestion,
    SurveySubmission,
)


class SurveyQuestionInline(admin.TabularInline):
    model = SurveyQuestion
    extra = 0
    fields = ("text", "question_type", "order")
    ordering = ("order",)


class SurveyOptionInline(admin.TabularInline):
    model = SurveyOption
    extra = 0
    fields = ("text", "order")
    ordering = ("order",)


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "created_at", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("title",)
    inlines = (SurveyQuestionInline,)


@admin.register(SurveyQuestion)
class SurveyQuestionAdmin(admin.ModelAdmin):
    list_display = ("survey", "text", "question_type", "order")
    list_filter = ("question_type", "survey")
    search_fields = ("text",)
    inlines = (SurveyOptionInline,)


@admin.register(SurveyOption)
class SurveyOptionAdmin(admin.ModelAdmin):
    list_display = ("question", "text", "order")
    search_fields = ("text",)


class SurveyAnswerItemInline(admin.TabularInline):
    model = SurveyAnswerItem
    extra = 0
    readonly_fields = ("question", "option")


@admin.register(SurveySubmission)
class SurveySubmissionAdmin(admin.ModelAdmin):
    list_display = ("student_fio", "student_login", "student_group", "survey", "edu_year", "submitted_at")
    list_filter = ("survey", "edu_year")
    search_fields = ("student_fio", "student_login", "student_group")
    readonly_fields = ("submitted_at",)
    inlines = (SurveyAnswerItemInline,)


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "work_phone")
    search_fields = ("user__email", "work_phone")


admin.site.register(SurveyAnswerItem)
