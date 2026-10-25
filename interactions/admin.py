from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import PostClap, Comment, CommentClap, ReadingList, BookmarkItem, Subscriber, Follow


class BookmarkItemInline(admin.TabularInline):
    model = BookmarkItem
    extra = 0
    autocomplete_fields = ["post"]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("author", "post", "parent", "is_deleted", "created_at")
    list_filter = ("is_deleted", "created_at")
    search_fields = ("author__username", "post__title", "content")
    autocomplete_fields = ["author", "post", "parent"]


@admin.register(PostClap)
class PostClapAdmin(admin.ModelAdmin):
    list_display = ("user", "post", "count", "updated_at")
    autocomplete_fields = ["user", "post"]


@admin.register(ReadingList)
class ReadingListAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "is_private", "created_at", "total_items")
    list_filter = ("is_private", "created_at")
    search_fields = ("title", "user__username")
    inlines = [BookmarkItemInline]

    def total_items(self, obj):
        return obj.items.count()


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "is_active", "subscribed_at")
    list_filter = ("is_active", "subscribed_at")
    search_fields = ("email",)


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("user", "author", "publication", "created_at")
    autocomplete_fields = ["user", "author", "publication"]