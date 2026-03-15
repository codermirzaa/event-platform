from django.db import models
from django.conf import settings
from django.utils import timezone


class Category(models.Model):
    """Event categories (e.g. Music, Sports, Workshop)"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Bootstrap icon name e.g. bi-music-note")

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Event(models.Model):
    """F-03: Event model"""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'
        CANCELLED = 'cancelled', 'Cancelled'

    # Core fields
    title = models.CharField(max_length=100)
    description = models.TextField(max_length=2000)
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='organized_events'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name='events'
    )

    # Date & location
    date = models.DateTimeField()
    location = models.CharField(max_length=255)

    # Ticket info
    capacity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # Media
    cover_image = models.ImageField(upload_to='events/covers/', blank=True, null=True)
    cover_image_url = models.URLField(blank=True)

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date']

    def __str__(self):
        return self.title

    @property
    def is_free(self):
        return self.price == 0

    @property
    def booked_count(self):
        return self.bookings.filter(status=Booking.Status.CONFIRMED).count()

    @property
    def available_spots(self):
        return self.capacity - self.booked_count

    @property
    def is_full(self):
        return self.available_spots <= 0

    @property
    def is_upcoming(self):
        return self.date > timezone.now()

    def get_cover(self):
        """Return cover image URL (uploaded file or external URL)."""
        if self.cover_image:
            return self.cover_image.url
        if self.cover_image_url:
            return self.cover_image_url
        return None


class Booking(models.Model):
    """F-05: Ticket booking model"""

    class Status(models.TextChoices):
        CONFIRMED = 'confirmed', 'Confirmed'
        CANCELLED = 'cancelled', 'Cancelled'

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='bookings')
    attendee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    reference = models.CharField(max_length=20, unique=True, editable=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIRMED)
    booked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # One booking per attendee per event
        unique_together = ('event', 'attendee')
        ordering = ['-booked_at']

    def __str__(self):
        return f"{self.reference} — {self.attendee.username} @ {self.event.title}"

    def save(self, *args, **kwargs):
        # Auto-generate unique reference number
        if not self.reference:
            import uuid
            self.reference = 'EVT-' + str(uuid.uuid4()).upper()[:8]
        super().save(*args, **kwargs)

    @property
    def can_cancel(self):
        """Attendee can cancel up to 24 hours before event."""
        from datetime import timedelta
        return (
            self.status == self.Status.CONFIRMED and
            self.event.date > timezone.now() + timedelta(hours=24)
        )
