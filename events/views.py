from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone

from .models import Event, Booking, Category, Review
from .forms import EventForm, EventSearchForm, ReviewForm
from accounts.decorators import organizer_required, admin_required, role_required


def event_list(request):
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
    event = get_object_or_404(Event, pk=pk)

    if event.status != Event.Status.PUBLISHED:
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if event.organizer != request.user and not request.user.is_platform_admin:
            messages.error(request, "This event is not available.")
            return redirect('events:list')

    user_booking = None
    user_review = None
    can_review = False

    if request.user.is_authenticated:
        user_booking = Booking.objects.filter(event=event, attendee=request.user).first()
        user_review = Review.objects.filter(event=event, author=request.user).first()
        can_review = not user_review  # Hər login olmuş istifadəçi rəy yaza bilər

    reviews = event.reviews.select_related('author').all()

    return render(request, 'events/event_detail.html', {
        'event': event,
        'user_booking': user_booking,
        'user_review': user_review,
        'can_review': can_review,
        'reviews': reviews,
    })


@organizer_required
def event_create(request):
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

    return render(request, 'events/event_form.html', {'form': form, 'action': 'Create'})


@organizer_required
def event_edit(request, pk):
    event = get_object_or_404(Event, pk=pk)

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

    return render(request, 'events/event_form.html', {'form': form, 'action': 'Edit', 'event': event})


@organizer_required
def event_cancel(request, pk):
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
    events = Event.objects.filter(organizer=request.user).annotate(
        booking_count=Count('bookings')
    ).order_by('-created_at')
    return render(request, 'events/my_events.html', {'events': events})


@organizer_required
def event_attendees(request, pk):
    event = get_object_or_404(Event, pk=pk, organizer=request.user)
    bookings = event.bookings.filter(
        status=Booking.Status.CONFIRMED
    ).select_related('attendee').order_by('booked_at')
    return render(request, 'events/event_attendees.html', {'event': event, 'bookings': bookings})


@login_required
def book_ticket(request, pk):
    event = get_object_or_404(Event, pk=pk, status=Event.Status.PUBLISHED)

    if event.organizer == request.user:
        messages.error(request, "You cannot book your own event.")
        return redirect('events:detail', pk=pk)

    if Booking.objects.filter(event=event, attendee=request.user).exists():
        messages.warning(request, "You have already booked this event.")
        return redirect('events:detail', pk=pk)

    if event.is_full:
        messages.error(request, "Sorry, this event is fully booked.")
        return redirect('events:detail', pk=pk)

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
    booking = get_object_or_404(Booking, pk=pk, attendee=request.user)

    from .utils import generate_qr_code
    qr_data = (
        f"EventHub Ticket\n"
        f"Ref: {booking.reference}\n"
        f"Event: {booking.event.title}\n"
        f"Date: {booking.event.date.strftime('%d %b %Y, %H:%M')}\n"
        f"Attendee: {booking.attendee.get_full_name() or booking.attendee.username}"
    )
    qr_code = generate_qr_code(qr_data)

    return render(request, 'events/booking_confirmation.html', {'booking': booking, 'qr_code': qr_code})


@login_required
def view_ticket(request, pk):
    booking = get_object_or_404(Booking, pk=pk, attendee=request.user)

    from .utils import generate_qr_code
    qr_data = (
        f"EventHub Ticket\n"
        f"Ref: {booking.reference}\n"
        f"Event: {booking.event.title}\n"
        f"Date: {booking.event.date.strftime('%d %b %Y, %H:%M')}\n"
        f"Location: {booking.event.location}\n"
        f"Attendee: {booking.attendee.get_full_name() or booking.attendee.username}"
    )
    qr_code = generate_qr_code(qr_data)

    return render(request, 'events/ticket.html', {'booking': booking, 'qr_code': qr_code})


@login_required
def cancel_booking(request, pk):
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


@login_required
def payment(request, pk):
    event = get_object_or_404(Event, pk=pk, status=Event.Status.PUBLISHED)

    if event.is_free:
        return redirect('events:book', pk=pk)

    if Booking.objects.filter(event=event, attendee=request.user).exists():
        messages.warning(request, "You have already booked this event.")
        return redirect('events:detail', pk=pk)

    if event.is_full:
        messages.error(request, "Sorry, this event is fully booked.")
        return redirect('events:detail', pk=pk)

    if not event.is_upcoming:
        messages.error(request, "This event has already passed.")
        return redirect('events:detail', pk=pk)

    if request.method == 'POST':
        card_number = request.POST.get('card_number', '').replace(' ', '')
        expiry = request.POST.get('expiry', '')
        cvv = request.POST.get('cvv', '')
        name = request.POST.get('card_name', '')

        errors = []
        if len(card_number) != 16 or not card_number.isdigit():
            errors.append("Invalid card number.")
        if not expiry or len(expiry) != 5:
            errors.append("Invalid expiry date.")
        if len(cvv) not in [3, 4] or not cvv.isdigit():
            errors.append("Invalid CVV.")
        if not name.strip():
            errors.append("Cardholder name is required.")

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'events/payment.html', {'event': event})

        booking = Booking.objects.create(event=event, attendee=request.user)
        messages.success(request, f'Payment successful! Booking confirmed: {booking.reference}')
        return redirect('events:booking_confirmation', pk=booking.pk)

    return render(request, 'events/payment.html', {'event': event})


@admin_required
def admin_events(request):
    events = Event.objects.all().select_related('organizer', 'category').annotate(
        booking_count=Count('bookings')
    ).order_by('-created_at')
    return render(request, 'events/admin_events.html', {'events': events})


@admin_required
def admin_event_action(request, pk):
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


@role_required('organizer', 'admin')
def verify_ticket(request):
    result = None
    reference = ''

    if request.method == 'POST':
        reference = request.POST.get('reference', '').strip().upper()
        try:
            booking = Booking.objects.select_related('event', 'attendee').get(reference=reference)

            if not request.user.is_platform_admin and booking.event.organizer != request.user:
                result = {'status': 'error', 'message': 'You do not have permission to verify this ticket.'}
            elif booking.status == Booking.Status.CANCELLED:
                result = {'status': 'invalid', 'message': 'This ticket has been cancelled.', 'booking': booking}
            elif booking.is_used:
                result = {'status': 'used', 'message': f'Already used at {booking.used_at.strftime("%d %b %Y, %H:%M") if booking.used_at else "unknown time"}.', 'booking': booking}
            else:
                booking.is_used = True
                booking.used_at = timezone.now()
                booking.save()
                result = {'status': 'valid', 'message': 'Ticket is valid! Entry granted.', 'booking': booking}

        except Booking.DoesNotExist:
            result = {'status': 'notfound', 'message': f'No ticket found with reference "{reference}".'}

    return render(request, 'events/verify_ticket.html', {'result': result, 'reference': reference})


@login_required
def add_review(request, pk):
    """F-10: Attendee adds a review for a past event."""
    event = get_object_or_404(Event, pk=pk)

    if Review.objects.filter(event=event, author=request.user).exists():
        messages.warning(request, "You have already reviewed this event.")
        return redirect('events:detail', pk=pk)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            Review.objects.create(
                event=event,
                author=request.user,
                rating=int(form.cleaned_data['rating']),
                comment=form.cleaned_data['comment'],
            )
            messages.success(request, "Your review has been submitted!")
            return redirect('events:detail', pk=pk)
    else:
        form = ReviewForm()

    return render(request, 'events/add_review.html', {'event': event, 'form': form})
