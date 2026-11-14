"""Django admin configuration for the learning system."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.apps import apps
from django.contrib.auth import get_user_model


@admin.register(get_user_model())
class LearningSystemUserAdmin(UserAdmin):
    """Expose the custom user model and its application role fields."""

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "status",
        "is_staff",
        "is_active",
    )
    list_filter = ("role", "status", "is_staff", "is_active", "is_superuser")
    search_fields = ("username", "email", "first_name", "last_name")
    fieldsets = UserAdmin.fieldsets + (
        ("Learning system access", {"fields": ("role", "status", "phone_number")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Learning system access", {"fields": ("role", "status", "phone_number")}),
    )


# Make the application's data layer manageable from Django admin. The built-in
# auth Group model is registered by django.contrib.auth.admin.
for model in apps.get_app_config("learning_system").get_models():
    if model not in admin.site._registry:
        admin.site.register(model)
