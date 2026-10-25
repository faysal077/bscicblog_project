from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils.timesince import timesince

from .models import Notification


@login_required
def notification_list(request):
    """Main notifications page."""
    notifications = (
        Notification.objects.filter(recipient=request.user)
        .select_related("actor", "target_post")
        .order_by("-created_at")[:50]
    )
    return render(request, "notifications/notification_list.html", {"notifications": notifications})


@login_required
def unread_count_api(request):
    """Polling endpoint returning the raw integer count of unread notifications."""
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({"unread_count": count})


@login_required
def dropdown_notifications_api(request):
    """Returns the 6 most recent notifications formatted for the navbar widget."""
    notifications = (
        Notification.objects.filter(recipient=request.user)
        .select_related("actor", "target_post")
        .order_by("-created_at")[:6]
    )

    data = []
    for n in notifications:
        data.append({
            "id": n.id,
            "actor": n.actor.full_name or n.actor.username,
            "actor_avatar": n.actor.avatar.url if n.actor.avatar else None,
            "verb": n.get_verb_display(),
            "target_title": n.target_post.title if n.target_post else "",
            "target_url": n.target_url or (n.target_post.get_absolute_url() if n.target_post else "#"),
            "is_read": n.is_read,
            "created_at": f"{timesince(n.created_at)} ago"
        })

    return JsonResponse({"notifications": data})


@login_required
@require_POST
def mark_as_read(request, notification_id):
    """Marks a single alert as read."""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return JsonResponse({"success": True})


@login_required
@require_POST
def mark_all_as_read(request):
    """Marks all unread alerts for the active user as read."""
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return JsonResponse({"success": True})