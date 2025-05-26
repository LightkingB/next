from django.contrib import admin
from .models import CustomUser, Role, Faculty, FacultyTranscript, \
    RegistrationTranscript, CategoryTranscript, Speciality
from django.contrib.auth.admin import UserAdmin


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
admin.site.register(Faculty)
admin.site.register(Speciality)
admin.site.register(FacultyTranscript)
admin.site.register(CategoryTranscript)


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
