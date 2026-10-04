from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db.models.signals import pre_delete
from django.dispatch import receiver

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
