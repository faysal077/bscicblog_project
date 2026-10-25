from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import PostEvent, PostRead, PostMetricsSummary


@admin.register(PostEvent)
class PostEventAdmin(admin.ModelAdmin):
    list_display = ("post", "user", "ip_address", "created_at")
    list_filter = ("created_at",)
    search_fields = ("post__title", "user__username", "ip_address", "referrer")
    autocomplete_fields = ["post", "user"]


@admin.register(PostRead)
class PostReadAdmin(admin.ModelAdmin):
    list_display = ("post", "user", "scroll_percentage", "time_spent_seconds", "is_completed_read", "updated_at")
    list_filter = ("is_completed_read", "created_at")
    search_fields = ("post__title", "user__username", "session_key")
    autocomplete_fields = ["post", "user"]


@admin.register(PostMetricsSummary)
class PostMetricsSummaryAdmin(admin.ModelAdmin):
    list_display = ("post", "date", "views_count", "reads_count")
    list_filter = ("date",)
    search_fields = ("post__title",)
    autocomplete_fields = ["post"]