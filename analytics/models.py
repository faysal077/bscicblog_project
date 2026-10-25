from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from posts.models import Post


class PostEvent(models.Model):
    """Logs individual visitor impression hits and referral origins."""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="analytics_events")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="analytics_events"
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    referrer = models.URLField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("post event")
        verbose_name_plural = _("post events")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Impression on {self.post.title} at {self.created_at}"


class PostRead(models.Model):
    """Tracks verified reading depth and active dwell time via client beacons."""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="reads")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reading_logs"
    )
    session_key = models.CharField(max_length=40, blank=True, db_index=True)
    scroll_percentage = models.PositiveSmallIntegerField(default=0)
    time_spent_seconds = models.PositiveIntegerField(default=0)
    is_completed_read = models.BooleanField(
        default=False,
        help_text=_("True if reader scrolled >= 80% with adequate dwell time.")
    )
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("post read session")
        verbose_name_plural = _("post read sessions")
        ordering = ["-updated_at"]

    def __str__(self):
        status = "Completed Read" if self.is_completed_read else "Partial Read"
        return f"{status} ({self.scroll_percentage}%) on {self.post.title}"


class PostMetricsSummary(models.Model):
    """Pre-computed daily summary record per post for Chart.js performance."""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="daily_metrics")
    date = models.DateField(db_index=True)
    views_count = models.PositiveIntegerField(default=0)
    reads_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = _("post metrics summary")
        verbose_name_plural = _("post metrics summaries")
        unique_together = ("post", "date")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.post.title} on {self.date} (Views: {self.views_count}, Reads: {self.reads_count})"