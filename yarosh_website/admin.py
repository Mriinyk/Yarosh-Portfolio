from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import NotRegistered
from django.urls import reverse
from django.utils.html import format_html
from django.utils.text import Truncator

from .models import ContactRequest

User = get_user_model()

try:
    admin.site.unregister(User)
except NotRegistered:
    pass


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "is_active", "is_staff", "date_joined")
    list_filter = ("is_active", "is_staff", "is_superuser", "groups")
    search_fields = ("username", "email", "first_name", "last_name")


@admin.register(ContactRequest)
class ContactRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "contact_method",
        "social_username",
        "message_preview",
        "created_at",
        "telegram_message_id",
    )
    list_filter = ("contact_method", "created_at")
    search_fields = ("social_username", "message")
    readonly_fields = ("created_at", "telegram_message_id")

    @admin.display(description="Повідомлення")
    def message_preview(self, obj):
        return format_html(
            '<a href="{}" title="{}">{}</a>',
            reverse(
                "admin:yarosh_website_contactrequest_change",
                args=(obj.pk,),
            ),
            obj.message,
            Truncator(obj.message).chars(60),
        )

    def delete_queryset(self, request, queryset):
        del request
        for contact_request in queryset:
            contact_request.delete()
