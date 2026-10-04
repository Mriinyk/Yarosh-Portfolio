import re
import uuid

from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.conf import settings
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils import timezone

from .contact_services import delete_telegram_notification


class User(AbstractUser):
    groups = models.ManyToManyField(
        Group,
        blank=True,
        related_name="user_set",
        related_query_name="user",
        db_table="auth_user_groups",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name="user_set",
        related_query_name="user",
        db_table="auth_user_user_permissions",
    )

    class Meta:
        db_table = "auth_user"
        swappable = "AUTH_USER_MODEL"
        verbose_name = "Users"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.username


class ContactRequest(models.Model):
    CONTACT_CHOICES = [
        ("telegram", "Telegram"),
        ("instagram", "Instagram"),
    ]

    contact_method = models.CharField(
        max_length=10,
        choices=CONTACT_CHOICES,
        default="telegram",
        verbose_name="Спосіб зв'язку",
    )
    social_username = models.CharField(
        max_length=100,
        verbose_name="Нікнейм",
    )
    message = models.TextField(verbose_name="Повідомлення")
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата створення",
    )
    telegram_message_id = models.BigIntegerField(
        blank=True,
        null=True,
        verbose_name="ID повідомлення в Telegram",
    )

    class Meta:
        verbose_name = "Orders"
        verbose_name_plural = "Orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_contact_method_display()}: {self.social_username}"


@receiver(pre_delete, sender=ContactRequest)
def delete_telegram_message_on_delete(**signal_kwargs):
    contact_request = signal_kwargs["instance"]
    if contact_request.telegram_message_id:
        delete_telegram_notification(contact_request)


class HeroSlide(models.Model):
    image_url = models.URLField(
        max_length=2048,
        verbose_name="Посилання на фото",
        help_text=(
            "Вставте пряме публічне посилання на фото або посилання на файл Google Drive "
            "(наприклад, drive.google.com/file/d/ID/view). Доступ до файлу має бути "
            "відкритий для всіх за посиланням. Посилання на альбоми Google Photos "
            "не підтримуються."
        ),
    )
    order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Порядок показу",
        help_text="Менше число — раніше відображення.",
    )
    is_active = models.BooleanField(default=True, verbose_name="Активний")

    class Meta:
        verbose_name = "Main slides"
        verbose_name_plural = "Main slides"
        ordering = ["order", "pk"]

    @staticmethod
    def normalize_google_drive_url(url):
        cleaned = url.strip()
        if "lh3.googleusercontent.com" in cleaned:
            return cleaned

        match = re.search(r"/d/([A-Za-z0-9_-]+)", cleaned)
        if not match:
            match = re.search(r"[?&]id=([A-Za-z0-9_-]+)", cleaned)
        if match:
            return f"https://lh3.googleusercontent.com/d/{match.group(1)}"
        return cleaned

    @property
    def direct_image_url(self):
        return self.normalize_google_drive_url(self.image_url)

    def save(self, *args, **kwargs):
        self.image_url = self.normalize_google_drive_url(self.image_url)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Слайд {self.order}: {self.image_url}"


class PhotoSessionType(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Тип фотосесії",
    )
    search_name = models.CharField(
        max_length=100,
        db_index=True,
        default="",
        editable=False,
    )
    order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Порядок показу",
    )

    class Meta:
        verbose_name = "Photo session type"
        verbose_name_plural = "Photo session types"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.search_name = self.name.casefold()
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"search_name"}
        super().save(*args, **kwargs)


class PhotoSession(models.Model):
    title = models.CharField(max_length=255, verbose_name="Назва фотосесії")
    search_title = models.CharField(
        max_length=255,
        db_index=True,
        default="",
        editable=False,
    )
    photo_type = models.ForeignKey(
        PhotoSessionType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="photo_sessions",
        verbose_name="Тип фотосесії",
    )
    cover_url = models.URLField(
        max_length=2048,
        verbose_name="Посилання на обкладинку",
        help_text="Підтримується пряме посилання або посилання Google Drive на файл.",
    )
    drive_folder_url = models.URLField(
        max_length=2048,
        verbose_name="Посилання на папку Google Drive",
        help_text="Папка має бути доступна всім, хто має посилання.",
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
        verbose_name="Дата публікації",
    )
    order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Порядок показу",
        help_text="Менше число — раніше відображення.",
    )
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="PhotoSessionLike",
        related_name="liked_photo_sessions",
        blank=True,
        verbose_name="Вподобання",
    )

    class Meta:
        verbose_name = "New Photoshoots"
        verbose_name_plural = "New Photoshoots"
        ordering = ["-created_at", "-pk"]

    @staticmethod
    def normalize_google_drive_url(url):
        cleaned = url.strip()
        if "lh3.googleusercontent.com" in cleaned:
            return cleaned

        match = re.search(r"/d/([A-Za-z0-9_-]+)", cleaned)
        if not match:
            match = re.search(r"[?&]id=([A-Za-z0-9_-]+)", cleaned)
        if match:
            return f"https://lh3.googleusercontent.com/d/{match.group(1)}"
        return cleaned

    @property
    def direct_cover_url(self):
        return self.normalize_google_drive_url(self.cover_url)

    def get_drive_folder_id(self):
        match = re.search(r"/folders/([A-Za-z0-9_-]+)", self.drive_folder_url)
        if not match:
            match = re.search(r"[?&]id=([A-Za-z0-9_-]+)", self.drive_folder_url)
        return match.group(1) if match else None

    def save(self, *args, **kwargs):
        self.search_title = self.title.casefold()
        self.cover_url = self.normalize_google_drive_url(self.cover_url)
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {
                "cover_url",
                "search_title",
            }
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class PhotoSessionLike(models.Model):
    photo_session = models.ForeignKey(
        PhotoSession,
        on_delete=models.CASCADE,
        related_name="like_records",
        verbose_name="Фотосесія",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="photo_session_like_records",
        verbose_name="Користувач",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата")

    class Meta:
        verbose_name = "Photo session like"
        verbose_name_plural = "Photo session likes"
        constraints = [
            models.UniqueConstraint(
                fields=("photo_session", "user"),
                name="unique_photo_session_like",
            )
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user}: {self.photo_session}"


class PhotoSessionComment(models.Model):
    photo_session = models.ForeignKey(
        PhotoSession,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="Фотосесія",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="photo_session_comments",
        verbose_name="Автор",
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="replies",
        verbose_name="Батьківський коментар",
    )
    text = models.TextField(max_length=2000, verbose_name="Коментар")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата")

    class Meta:
        verbose_name = "Photo session comment"
        verbose_name_plural = "Photo session comments"
        ordering = ["created_at", "pk"]

    def __str__(self):
        return f"{self.user}: {self.photo_session}"


class SiteVisitor(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="Ідентифікатор",
    )
    first_seen = models.DateTimeField(auto_now_add=True, verbose_name="Перший візит")

    class Meta:
        verbose_name = "Унікальний відвідувач"
        verbose_name_plural = "Унікальні відвідувачі"
        ordering = ["-first_seen"]

    def __str__(self):
        return str(self.id)


class PhotoSessionShare(models.Model):
    photo_session = models.ForeignKey(
        PhotoSession,
        on_delete=models.CASCADE,
        related_name="shares",
        verbose_name="Фотосесія",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="photo_session_shares",
        verbose_name="Користувач",
    )
    visitor = models.ForeignKey(
        SiteVisitor,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="photo_session_shares",
        verbose_name="Пристрій",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата")

    class Meta:
        verbose_name = "Photo session share"
        verbose_name_plural = "Photo session shares"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.photo_session} — {self.created_at:%d.%m.%Y %H:%M}"


class Biography(models.Model):
    title = models.CharField(
        max_length=255,
        default="ПРО МЕНЕ",
        verbose_name="Заголовок",
    )
    text = models.TextField(
        verbose_name="Текст біографії",
        help_text="Розділяйте абзаци порожнім рядком.",
    )
    photo = models.ImageField(
        upload_to="biography/",
        blank=True,
        verbose_name="Фото",
        help_text=(
            "Якщо фото не завантажено, використовується стандартне "
            "зображення Biographical.jpg."
        ),
    )

    class Meta:
        verbose_name = "Biography"
        verbose_name_plural = "Biography"
        ordering = ["pk"]

    def __str__(self):
        return self.title
