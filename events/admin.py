from django.contrib import admin
from .models import Event, Booking, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'organizer', 'category', 'date', 'status', 'capacity', 'booked_count')
    list_filter = ('status', 'category')
    search_fields = ('title', 'organizer__username')
    ordering = ('-created_at',)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('reference', 'attendee', 'event', 'status', 'booked_at')
    list_filter = ('status',)
    search_fields = ('reference', 'attendee__username', 'event__title')
