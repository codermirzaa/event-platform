from functools import wraps
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


# ─────────────────────────────────────────────
#  Function-based view decorators
# ─────────────────────────────────────────────

def role_required(*roles):
    """
    Decorator that checks if the logged-in user has one of the given roles.
    Usage:
        @role_required('organizer', 'admin')
        def my_view(request): ...
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.role not in roles and not request.user.is_superuser:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def organizer_required(view_func):
    """Shortcut decorator — only organizers (and admins) can access."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not (request.user.is_organizer or request.user.is_platform_admin):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """Shortcut decorator — only platform admins can access."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_platform_admin:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────
#  Class-based view mixins
# ─────────────────────────────────────────────

class OrganizerRequiredMixin(LoginRequiredMixin):
    """CBV mixin — only organizers and admins."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.is_organizer or request.user.is_platform_admin):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class AdminRequiredMixin(LoginRequiredMixin):
    """CBV mixin — only platform admins."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_platform_admin:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
