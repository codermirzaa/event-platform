from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """
    Custom User model with role-based access control.
    Roles: Attendee, Organizer, Admin
    """

    class Role(models.TextChoices):
        ATTENDEE = 'attendee', 'Attendee'
        ORGANIZER = 'organizer', 'Organizer'
        ADMIN = 'admin', 'Admin'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.ATTENDEE,
    )

    # Extra profile fields
    phone = models.CharField(max_length=20, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    # --- Convenience properties ---

    @property
    def is_attendee(self):
        return self.role == self.Role.ATTENDEE

    @property
    def is_organizer(self):
        return self.role == self.Role.ORGANIZER

    @property
    def is_platform_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser
