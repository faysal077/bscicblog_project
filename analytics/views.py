from django.shortcuts import render

# Create your views here.
import json
from datetime import timedelta
from urllib.parse import urlparse

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Sum
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from posts.models import Post
from .models import PostEvent, PostMetricsSummary, PostRead


@csrf_exempt
@require_POST
def record_post_view(request, post_id):
    """Endpoint triggered asynchronously when an article detail page mounts."""
    post = get_object_or_404(Post, id=post_id)

    # Resolve IP address
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")

    user_agent = request.META.get("HTTP_USER_AGENT", "")[:255]
    referrer = request.META.get("HTTP_REFERER", "")[:500]

    # Create raw event record
    PostEvent.objects.create(
        post=post,
        user=request.user if request.user.is_authenticated else None,
        ip_address=ip,
        user_agent=user_agent,
        referrer=referrer,
    )

    # Sync daily summary
    today = timezone.now().date()
    summary, _ = PostMetricsSummary.objects.get_or_create(post=post, date=today)
    summary.views_count += 1
    summary.save(update_fields=["views_count"])

    return JsonResponse({"success": True})


@csrf_exempt
@require_POST
def record_read_beacon(request, post_id):
    """Receives periodic read beacons tracking scroll depth and dwell time."""
    post = get_object_or_404(Post, id=post_id)

    try:
        data = json.loads(request.body)
        percentage = min(100, max(0, int(data.get("percentage", 0))))
        time_spent = max(0, int(data.get("time_spent", 0)))
    except (ValueError, TypeError, json.JSONDecodeError):
        return HttpResponseBadRequest("Invalid beacon payload")

    if not request.session.session_key:
        request.session.save()
    session_key = request.session.session_key

    # Retrieve or initialize reading log for current session
    read_log, created = PostRead.objects.get_or_create(
        post=post,
        session_key=session_key,
        defaults={
            "user": request.user if request.user.is_authenticated else None,
            "scroll_percentage": percentage,
            "time_spent_seconds": time_spent,
        }
    )

    if not created:
        if percentage > read_log.scroll_percentage:
            read_log.scroll_percentage = percentage
        read_log.time_spent_seconds = max(read_log.time_spent_seconds, time_spent)
        if request.user.is_authenticated and not read_log.user:
            read_log.user = request.user

    # Determine completed read threshold (scroll depth >= 80% and dwell >= 25s)
    was_completed = read_log.is_completed_read
    if read_log.scroll_percentage >= 80 and read_log.time_spent_seconds >= 25:
        read_log.is_completed_read = True

    read_log.save()

    # Update summary increment once per session on status transition
    if not was_completed and read_log.is_completed_read:
        today = timezone.now().date()
        summary, _ = PostMetricsSummary.objects.get_or_create(post=post, date=today)
        summary.reads_count += 1
        summary.save(update_fields=["reads_count"])

    return JsonResponse({"success": True, "completed": read_log.is_completed_read})


@login_required
def analytics_dashboard(request):
    """Author-facing metrics dashboard showing 30-day graphs and story data."""
    user = request.user

    # Scoped to stories written by author unless super admin
    if user.is_super_admin:
        posts = Post.objects.all().select_related("category")
    else:
        posts = Post.objects.filter(author=user).select_related("category")

    total_views = posts.aggregate(Sum("visit_count"))["visit_count__sum"] or 0

    # Aggregate verified reads
    total_reads = PostRead.objects.filter(post__in=posts, is_completed_read=True).count()

    read_ratio = round((total_reads / total_views * 100), 1) if total_views > 0 else 0.0

    # Total claps across posts
    total_claps = sum(p.total_claps_count for p in posts)

    # Build 30-day chronological dataset for Chart.js
    today = timezone.now().date()
    daily_dates = []
    daily_views = []
    daily_reads = []

    for i in range(29, -1, -1):
        target_date = today - timedelta(days=i)
        daily_dates.append(target_date.strftime("%b %d"))

        metrics = PostMetricsSummary.objects.filter(
            post__in=posts,
            date=target_date
        ).aggregate(
            views=Sum("views_count"),
            reads=Sum("reads_count")
        )
        daily_views.append(metrics["views"] or 0)
        daily_reads.append(metrics["reads"] or 0)

    # Attach computed counters to post records
    for p in posts:
        p.total_views_count = p.visit_count
        p.total_reads_count = p.reads.filter(is_completed_read=True).count()

    context = {
        "author_posts": posts,
        "total_views": total_views,
        "total_reads": total_reads,
        "read_ratio": read_ratio,
        "total_claps": total_claps,
        "daily_dates_json": json.dumps(daily_dates),
        "daily_views_json": json.dumps(daily_views),
        "daily_reads_json": json.dumps(daily_reads),
    }
    return render(request, "analytics/dashboard.html", context)


@login_required
def post_stats_detail(request, post_id):
    """Detailed analytics breakdown for a single story."""
    post = get_object_or_404(Post, id=post_id)

    # Authorization
    if not (request.user == post.author or request.user.is_super_admin or request.user.is_officer):
        raise PermissionDenied("You are not permitted to inspect analytics for this story.")

    post.total_views_count = post.visit_count
    post.total_reads_count = post.reads.filter(is_completed_read=True).count()

    # Domain-level aggregation for referral sources
    raw_referrers = (
        PostEvent.objects.filter(post=post)
        .exclude(referrer="")
        .values("referrer")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    clean_referrers = []
    for item in raw_referrers:
        parsed = urlparse(item["referrer"]).netloc or item["referrer"]
        clean_referrers.append({"referrer": parsed, "count": item["count"]})

    context = {
        "post": post,
        "top_referrers": clean_referrers,
    }
    return render(request, "analytics/post_stats.html", context)


@login_required
def post_stats_api(request, post_id):
    """API endpoint providing a 30-day timeline payload for single-post bar charts."""
    post = get_object_or_404(Post, id=post_id)

    if not (request.user == post.author or request.user.is_super_admin or request.user.is_officer):
        raise PermissionDenied("Access denied.")

    today = timezone.now().date()
    daily_breakdown = []

    for i in range(14, -1, -1):
        target_date = today - timedelta(days=i)
        summary = PostMetricsSummary.objects.filter(post=post, date=target_date).first()

        daily_breakdown.append({
            "date": target_date.strftime("%b %d"),
            "total_views": summary.views_count if summary else 0,
            "total_reads": summary.reads_count if summary else 0,
        })

    return JsonResponse({"daily_breakdown": daily_breakdown})