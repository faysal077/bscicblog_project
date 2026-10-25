from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Publication, PublicationMember


class PublicationMemberInline(admin.TabularInline):
    model = PublicationMember
    extra = 1
    autocomplete_fields = ["user"]
    fields = ("user", "role", "joined_at")
    readonly_fields = ("joined_at",)


@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "is_official", "created_at", "total_members_count")
    list_filter = ("is_official", "created_at")
    search_fields = ("name", "tagline", "description", "owner__username", "owner__email")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ["owner"]
    inlines = [PublicationMemberInline]

    @admin.display(description="Total Members")
    def total_members_count(self, obj):
        return obj.members.count()


@admin.register(PublicationMember)
class PublicationMemberAdmin(admin.ModelAdmin):
    list_display = ("user", "publication", "role", "joined_at")
    list_filter = ("role", "joined_at", "publication__is_official")
    search_fields = ("user__username", "user__email", "publication__name")
    autocomplete_fields = ["user", "publication"]