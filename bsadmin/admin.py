from django.contrib import admin
from .models import CustomUser, Role, Faculty, AcademicTranscript, CategoryTranscript, FacultyTranscript, \
    RegistrationTranscript
from django.contrib.auth.admin import UserAdmin


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ("email", "first_name", "last_name", "is_active", "is_staff")
    list_filter = ("is_active", "is_staff", "roles")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)
    filter_horizontal = ("roles",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "fathers_name")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "roles")}),
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
admin.site.register(FacultyTranscript)
admin.site.register(AcademicTranscript)
admin.site.register(CategoryTranscript)
admin.site.register(RegistrationTranscript)
