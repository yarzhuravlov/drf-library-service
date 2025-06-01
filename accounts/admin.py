from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from accounts.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):

    exclude = ("username",)

    readonly_fields = ("last_login", "created_at", "updated_at")

    fieldsets = (
        (
            None,
            {"fields": ("email", "password", "date_of_birth", "is_verified")},
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Important dates",
            {"fields": ("last_login", "created_at", "updated_at")},
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "date_of_birth"),
            },
        ),
    )
    list_display = (
        "email",
        "date_of_birth",
        "is_verified",
        "is_staff",
        "is_active",
    )
    search_fields = ("email",)
    ordering = ("email",)
    filter_horizontal = ("groups", "user_permissions")
