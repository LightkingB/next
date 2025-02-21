from django.contrib import admin
from .models import CustomUser, Role, Faculty, FacultyTranscript, \
    RegistrationTranscript, CategoryTranscript
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
admin.site.register(FacultyTranscript)
admin.site.register(CategoryTranscript)
admin.site.register(RegistrationTranscript)
