from django.conf import settings
from django.db import models


class Profile(models.Model):
    """Extra information for each user (one profile per user)."""

    class Role(models.TextChoices):
        MANAGER = 'manager', 'Project Manager'
        MEMBER = 'member', 'Team Member'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    phone = models.CharField(max_length=15, blank=True)
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username} ({self.get_role_display()})'