from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone

from .models import Event, Booking, Category
from .forms import EventForm, EventSearchForm
from accounts.decorators import organizer_required, admin_required


# ─────────────────────────────────────────────
#  F-04: Event Discovery
# ─────────────────────────────────────────────

def event_list(request):
    """Homepage — upcoming published events with search & filter."""
    form = EventSearchForm(request.GET)
    events = Event.objects.filter(
        status=Event.Status.PUBLISHED,
        date__gt=timezone.now()
    ).select_related('category', 'organizer')

    if form.is_valid():
        q = form.cleaned_data.get('q')
        category = form.cleaned_data.get('category')
        price_type = form.cleaned_data.get('price_type')
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')
        sort = form.cleaned_data.get('sort')

        if q:
            events = events.filter(Q(title__icontains=q) | Q(description__icontains=q))
        if category:
            events = events.filter(category=category)
        if price_type == 'free':
            events = events.filter(price=0)
        elif price_type == 'paid':
            events = events.filter(price__gt=0)
        if date_from:
            events = events.filter(date__date__gte=date_from)
        if date_to:
            events = events.filter(date__date__lte=date_to)
        if sort == 'popular':
            events = events.annotate(booking_count=Count('bookings')).order_by('-booking_count')
        else:
            events = events.order_by('date')

    categories = Category.objects.all()
    return render(request, 'events/event_list.html', {
        'events': events,
        'form': form,
        'categories': categories,
    })


def event_detail(request, pk):
    """Event detail page."""
    event = get_object_or_404(Event, pk=pk)

    # Only show published events to non-organizers
    if event.status != Event.Status.PUBLISHED:
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if event.organizer != request.user and not request.user.is_platform_admin:
            messages.error(request, "This event is not available.")
            return redirect('events:list')

    user_booking = None
    if request.user.is_authenticated:
        user_booking = Booking.objects.filter(event=event, attendee=request.user).first()

    return render(request, 'events/event_detail.html', {
        'event': event,
        'user_booking': user_booking,
    })


# ─────────────────────────────────────────────
#  F-03: Event Management (Organizer)
# ─────────────────────────────────────────────

@organizer_required
def event_create(request):
    """Organizer creates a new event."""
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            messages.success(request, f'Event "{event.title}" created successfully!')
            return redirect('events:detail', pk=event.pk)
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = EventForm()

    return render(request, 'events/event_form.html', {
        'form': form,
        'action': 'Create',
    })


@organizer_required
def event_edit(request, pk):
    """Organizer edits their event."""
    event = get_object_or_404(Event, pk=pk)

    # Only the organizer or admin can edit
    if event.organizer != request.user and not request.user.is_platform_admin:
        messages.error(request, "You can only edit your own events.")
        return redirect('events:detail', pk=pk)

    if event.status == Event.Status.CANCELLED:
        messages.error(request, "Cancelled events cannot be edited.")
        return redirect('events:detail', pk=pk)

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, f'Event "{event.title}" updated successfully!')
            return redirect('events:detail', pk=event.pk)
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = EventForm(instance=event)

    return render(request, 'events/event_form.html', {
        'form': form,
        'action': 'Edit',
        'event': event,
    })


@organizer_required
def event_cancel(request, pk):
    """Organizer cancels their event."""
    event = get_object_or_404(Event, pk=pk)

    if event.organizer != request.user and not request.user.is_platform_admin:
        messages.error(request, "You can only cancel your own events.")
        return redirect('events:detail', pk=pk)

    if request.method == 'POST':
        event.status = Event.Status.CANCELLED
        event.save()
        messages.success(request, f'Event "{event.title}" has been cancelled.')
        return redirect('events:my_events')

    return render(request, 'events/event_confirm_cancel.html', {'event': event})


@organizer_required
def my_events(request):
    """Organizer's event list."""
    events = Event.objects.filter(organizer=request.user).annotate(
        booking_count=Count('bookings')
    ).order_by('-created_at')

    return render(request, 'events/my_events.html', {'events': events})


@organizer_required
def event_attendees(request, pk):
    """Organizer views attendees for their event."""
    event = get_object_or_404(Event, pk=pk, organizer=request.user)
    bookings = event.bookings.filter(
        status=Booking.Status.CONFIRMED
    ).select_related('attendee').order_by('booked_at')

    return render(request, 'events/event_attendees.html', {
        'event': event,
        'bookings': bookings,
    })


# ─────────────────────────────────────────────
#  F-05: Ticket Booking
# ─────────────────────────────────────────────

@login_required
def book_ticket(request, pk):
    """Attendee books a ticket."""
    event = get_object_or_404(Event, pk=pk, status=Event.Status.PUBLISHED)

    # Organizers cannot book their own events
    if event.organizer == request.user:
        messages.error(request, "You cannot book your own event.")
        return redirect('events:detail', pk=pk)

    # Check if already booked
    if Booking.objects.filter(event=event, attendee=request.user).exists():
        messages.warning(request, "You have already booked this event.")
        return redirect('events:detail', pk=pk)

    # Check capacity
    if event.is_full:
        messages.error(request, "Sorry, this event is fully booked.")
        return redirect('events:detail', pk=pk)

    # Check event is in future
    if not event.is_upcoming:
        messages.error(request, "This event has already passed.")
        return redirect('events:detail', pk=pk)

    if request.method == 'POST':
        booking = Booking.objects.create(event=event, attendee=request.user)
        messages.success(request, f'Booking confirmed! Your reference: {booking.reference}')
        return redirect('events:booking_confirmation', pk=booking.pk)

    return render(request, 'events/book_confirm.html', {'event': event})


@login_required
def booking_confirmation(request, pk):
    """Booking confirmation page with reference number."""
    booking = get_object_or_404(Booking, pk=pk, attendee=request.user)
    return render(request, 'events/booking_confirmation.html', {'booking': booking})


@login_required
def cancel_booking(request, pk):
    """Attendee cancels their booking."""
    booking = get_object_or_404(Booking, pk=pk, attendee=request.user)

    if not booking.can_cancel:
        messages.error(request, "This booking cannot be cancelled (less than 24 hours before event).")
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        booking.status = Booking.Status.CANCELLED
        booking.save()
        messages.success(request, f'Booking {booking.reference} has been cancelled.')
        return redirect('accounts:dashboard')

    return render(request, 'events/cancel_booking_confirm.html', {'booking': booking})


# ─────────────────────────────────────────────
#  F-07: Admin Moderation
# ─────────────────────────────────────────────

@admin_required
def admin_events(request):
    """Admin views and moderates all events."""
    events = Event.objects.all().select_related('organizer', 'category').annotate(
        booking_count=Count('bookings')
    ).order_by('-created_at')

    return render(request, 'events/admin_events.html', {'events': events})


@admin_required
def admin_event_action(request, pk):
    """Admin approves, rejects, or deletes an event."""
    event = get_object_or_404(Event, pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'publish':
            event.status = Event.Status.PUBLISHED
            event.save()
            messages.success(request, f'Event "{event.title}" published.')
        elif action == 'cancel':
            event.status = Event.Status.CANCELLED
            event.save()
            messages.success(request, f'Event "{event.title}" cancelled.')
        elif action == 'delete':
            event.delete()
            messages.success(request, 'Event deleted.')
            return redirect('events:admin_events')

    return redirect('events:admin_events')
