from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib.auth.mixins import AccessMixin


def role_required(allowed_roles):
    """Decorator checking if user has any of the specified roles."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("accounts:login")
            if request.user.is_superuser or request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied("You do not hold adequate departmental clearance for this action.")
        return _wrapped_view
    return decorator


class OfficerRequiredMixin(AccessMixin):
    """Verify that current user is an officer or administrator."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_officer:
            raise PermissionDenied("BSCIC Officer authorization required.")
        return super().dispatch(request, *args, **kwargs)


class WriterRequiredMixin(AccessMixin):
    """Verify that current user is authorized to create/draft articles."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.can_write:
            raise PermissionDenied("Contributor authorization required.")
        return super().dispatch(request, *args, **kwargs)