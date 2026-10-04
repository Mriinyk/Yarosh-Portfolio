from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import NotRegistered
from django.urls import reverse
from django.utils.html import format_html
from django.utils.text import Truncator

from .models import Biography, ContactRequest, HeroSlide, PhotoSession

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


@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    list_display = ("order", "image_preview", "image_url", "is_active")
    list_display_links = ("image_preview",)
    list_editable = ("order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("image_url",)
    ordering = ("order", "pk")

    @admin.display(description="Попередній перегляд")
    def image_preview(self, obj):
        return format_html(
            '<img src="{}" alt="" style="width: 120px; height: 68px; '
            'object-fit: cover; border-radius: 4px;">',
            obj.image_url,
        )


@admin.register(PhotoSession)
class PhotoSessionAdmin(admin.ModelAdmin):
    list_display = ("order", "title", "cover_preview", "is_active")
    list_display_links = ("title",)
    list_editable = ("order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("title", "cover_url", "drive_folder_url")
    ordering = ("order", "pk")

    @admin.display(description="Обкладинка")
    def cover_preview(self, obj):
        return format_html(
            '<img src="{}" alt="" style="width: 120px; height: 68px; '
            'object-fit: cover; border-radius: 4px;">',
            obj.direct_cover_url,
        )


@admin.register(Biography)
class BiographyAdmin(admin.ModelAdmin):
    list_display = ("title", "photo_preview")
    search_fields = ("title", "text")
    readonly_fields = ("photo_preview",)

    @admin.display(description="Фото")
    def photo_preview(self, obj):
        if not obj.photo:
            return "Стандартне зображення (Biographical.jpg)"
        return format_html(
            '<img src="{}" alt="" style="width: 120px; height: 68px; '
            'object-fit: cover; border-radius: 8px;">',
            obj.photo.url,
        )
