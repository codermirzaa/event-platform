from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied

from .forms import RegisterForm, LoginForm, ProfileUpdateForm
from .models import CustomUser


# ─────────────────────────────────────────────
#  Register
# ─────────────────────────────────────────────

def register_view(request):
    """
    F-01: User registration.
    - Validates form (unique email, password strength).
    - Saves user with hashed password (Django uses PBKDF2/bcrypt via password hashers).
    - Logs user in immediately after registration.
    - Redirects to role-specific dashboard.
    """
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome, {user.first_name or user.username}! Your account has been created.")
            return redirect('accounts:dashboard')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


# ─────────────────────────────────────────────
#  Login
# ─────────────────────────────────────────────

def login_view(request):
    """
    F-01: Login via username + password.
    Session maintained via Django session cookies.
    """
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            # Redirect to 'next' param if present
            next_url = request.GET.get('next', 'accounts:dashboard')
            return redirect(next_url)
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm(request)

    return render(request, 'accounts/login.html', {'form': form})


# ─────────────────────────────────────────────
#  Logout
# ─────────────────────────────────────────────

def logout_view(request):
    """F-01: Logout clears session."""
    if request.method == 'POST':
        logout(request)
        messages.info(request, "You have been logged out.")
        return redirect('accounts:login')
    return redirect('accounts:dashboard')


# ─────────────────────────────────────────────
#  Dashboard — role-based redirect hub
# ─────────────────────────────────────────────

@login_required
def dashboard_view(request):
    """
    F-02: Role-based dashboard.
    Each role sees their own dashboard template.
    """
    from django.utils import timezone
    user = request.user

    if user.is_platform_admin:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        # lazy import to avoid circular
        try:
            from events.models import Event, Booking
            stats = {
                'total_users': User.objects.count(),
                'total_events': Event.objects.count(),
                'total_bookings': Booking.objects.count(),
                'pending_events': Event.objects.filter(status='draft').count(),
            }
        except Exception:
            stats = {}
        return render(request, 'accounts/dashboard_admin.html', {'user': user, 'stats': stats})

    elif user.is_organizer:
        try:
            from events.models import Event
            from django.db.models import Count
            events = Event.objects.filter(organizer=user).annotate(
                booking_count=Count('bookings')
            ).order_by('-created_at')[:5]
            stats = {
                'active': Event.objects.filter(organizer=user, status='published').count(),
                'draft': Event.objects.filter(organizer=user, status='draft').count(),
                'total_bookings': sum(e.booking_count for e in events),
            }
        except Exception:
            events, stats = [], {}
        return render(request, 'accounts/dashboard_organizer.html', {
            'user': user, 'events': events, 'stats': stats
        })

    else:
        try:
            from events.models import Booking
            upcoming = Booking.objects.filter(
                attendee=user,
                status='confirmed',
                event__date__gt=timezone.now()
            ).select_related('event').order_by('event__date')[:5]
            past = Booking.objects.filter(
                attendee=user,
                event__date__lte=timezone.now()
            ).select_related('event').order_by('-event__date')[:5]
        except Exception:
            upcoming, past = [], []
        return render(request, 'accounts/dashboard_attendee.html', {
            'user': user, 'upcoming': upcoming, 'past': past
        })


# ─────────────────────────────────────────────
#  Profile
# ─────────────────────────────────────────────

@login_required
def profile_view(request):
    """View and update own profile."""
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('accounts:profile')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, 'accounts/profile.html', {'form': form})
