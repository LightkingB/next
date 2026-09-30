from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, Role, Faculty, FacultyTranscript, \
    RegistrationTranscript, CategoryTranscript, Speciality, RegHistoryTranscript


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ("myedu_id", "email", "first_name", "last_name", "is_active", "is_staff")
    list_filter = ("is_active", "is_staff", "roles")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)
    filter_horizontal = ("roles",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("myedu_id", "first_name", "last_name", "fathers_name")}),
        ("Permissions", {"fields": ("is_worker", "is_active", "is_staff", "roles")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "first_name", "last_name"),
        }),
    )


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Role)
# admin.site.register(Faculty)
# admin.site.register(Speciality)
@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "short_name",
        "category",
        "myedu_faculty_id",
        "is_myedu",
        "visit",
    )
    list_display_links = ("id", "title")

    list_filter = (
        "category",
        "is_myedu",
        "visit",
    )

    search_fields = (
        "title",
        "short_name",
        "myedu_faculty_id",
    )

    list_editable = (
        "short_name",
        "category",
        "is_myedu",
        "visit",
    )

    list_per_page = 50
    ordering = ("title",)
    save_on_top = True
    show_full_result_count = True


@admin.register(Speciality)
class SpecialityAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "short_name",
        "code",
        "faculty",
        "myedu_spec_id",
        "visit",
    )
    list_display_links = ("id", "title")

    list_filter = (
        "faculty",
        "visit",
    )

    search_fields = (
        "title",
        "short_name",
        "code",
        "myedu_spec_id",
        "faculty__title",
    )

    list_editable = (
        "short_name",
        "code",
        "visit",
    )

    autocomplete_fields = (
        "faculty",
    )

    list_per_page = 50
    ordering = ("title",)
    save_on_top = True
    show_full_result_count = True


@admin.register(FacultyTranscript)
class FacultyTranscriptAdmin(admin.ModelAdmin):
    list_display = ('transcript_number', 'faculty',)
    search_fields = ('transcript_number',)


admin.site.register(CategoryTranscript)
admin.site.register(RegHistoryTranscript)


@admin.register(RegistrationTranscript)
class RegistrationTranscriptAdmin(admin.ModelAdmin):
    list_display = ('faculty_transcript', 'student_uuid', 'student_fio')
    search_fields = (
        'faculty_transcript__transcript_number',
        'student_fio'
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('faculty_transcript', )
