from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Post, Category, Tag, PostMediaAsset


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at", "total_posts_count")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}

    def total_posts_count(self, obj):
        return obj.posts.count()


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "category", "status", "is_approved", "is_featured", "visit_count", "published_at")
    list_filter = ("status", "is_approved", "is_featured", "category", "created_at")
    search_fields = ("title", "subtitle", "content_html", "author__username", "author__email")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ["author", "category", "publication", "tags"]
    date_hierarchy = "created_at"


@admin.register(PostMediaAsset)
class PostMediaAssetAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "post", "uploaded_at")
    list_filter = ("uploaded_at",)