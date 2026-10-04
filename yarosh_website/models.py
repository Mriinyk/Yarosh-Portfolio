from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission


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
