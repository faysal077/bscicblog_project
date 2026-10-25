from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "actor", "verb", "target_post", "is_read", "created_at")
    list_filter = ("verb", "is_read", "created_at")
    search_fields = ("recipient__username", "actor__username", "target_post__title")
    autocomplete_fields = ["recipient", "actor", "target_post"]