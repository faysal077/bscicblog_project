from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "full_name",
        "role",
        "is_verified",
        "is_staff",
        "is_active",
        "date_joined",
    )
    list_filter = ("role", "is_verified", "is_staff", "is_active", "date_joined")
    search_fields = ("username", "email", "full_name", "designation", "department")
    ordering = ("-date_joined",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal Information"), {"fields": ("full_name", "email", "avatar", "bio", "website_url")}),
        (_("BSCIC Office & Designation"), {"fields": ("role", "designation", "department", "is_verified")}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "full_name", "role", "password", "is_staff", "is_active"),
            },
        ),
    )
