from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Platform", {"fields": ("role", "email_verified")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Platform", {"fields": ("email", "role")}),)
    list_display = ("username", "email", "role", "is_staff", "is_active")
