from django.db import models

# Create your models here.
import math
import re
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from publications.models import Publication


class Category(models.Model):
    name = models.CharField(_("category name"), max_length=100, unique=True)
    slug = models.SlugField(_("slug"), max_length=120, unique=True)
    description = models.TextField(_("description"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("category")
        verbose_name_plural = _("categories")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("posts:category_posts", kwargs={"slug": self.slug})


class Tag(models.Model):
    name = models.CharField(_("tag name"), max_length=50, unique=True)
    slug = models.SlugField(_("slug"), max_length=60, unique=True)

    class Meta:
        verbose_name = _("tag")
        verbose_name_plural = _("tags")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("posts:tag_posts", kwargs={"slug": self.slug})


class Post(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        PUBLISHED = "published", _("Published")

    class Visibility(models.TextChoices):
        PUBLIC = "public", _("Public")
        UNLISTED = "unlisted", _("Unlisted")

    title = models.CharField(_("title"), max_length=255)
    subtitle = models.CharField(_("subtitle"), max_length=300, blank=True)
    slug = models.SlugField(_("slug"), max_length=280, unique=True, db_index=True)
    
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",
        verbose_name=_("author")
    )
    publication = models.ForeignKey(
        Publication,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
        verbose_name=_("publication hub")
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
        verbose_name=_("category")
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="posts", verbose_name=_("tags"))

    # Block-based Content Canvas & Media
    content_html = models.TextField(
        _("content HTML"),
        help_text=_("Rich block-based HTML markup representing paragraphs, lists, inline images, and blockquotes.")
    )
    featured_image = models.ImageField(
        _("featured thumbnail"),
        upload_to="posts/covers/%Y/%m/",
        blank=True,
        null=True
    )
    featured_image_caption = models.CharField(_("cover image caption"), max_length=255, blank=True)
    featured_image_alt = models.CharField(_("cover alt text"), max_length=255, blank=True)
    youtube_video_url = models.URLField(_("YouTube video link"), blank=True, null=True)

    # SEO Metadata
    meta_title = models.CharField(_("meta title"), max_length=160, blank=True)
    meta_description = models.CharField(_("meta description"), max_length=255, blank=True)

    # State & Moderation
    status = models.CharField(_("status"), max_length=15, choices=Status.choices, default=Status.DRAFT, db_index=True)
    visibility = models.CharField(_("visibility"), max_length=15, choices=Visibility.choices, default=Visibility.PUBLIC)
    is_approved = models.BooleanField(_("approved"), default=False, db_index=True)
    is_featured = models.BooleanField(_("featured"), default=False, db_index=True)

    # Calculated & Aggregate Metrics
    reading_time_minutes = models.PositiveIntegerField(_("reading time (min)"), default=1)
    visit_count = models.PositiveIntegerField(_("total views"), default=0, db_index=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(_("published at"), null=True, blank=True, db_index=True)

    class Meta:
        verbose_name = _("post")
        verbose_name_plural = _("posts")
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "is_approved", "is_featured"]),
            models.Index(fields=["category", "status", "is_approved"]),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("posts:post_detail", kwargs={"slug": self.slug})

    @property
    def total_claps_count(self):
        # Relies on interactions app reverse relation
        if hasattr(self, "claps"):
            return self.claps.aggregate(models.Sum("count"))["count__sum"] or 0
        return 0

    @property
    def total_comments_count(self):
        if hasattr(self, "comments"):
            return self.comments.count()
        return 0

    @property
    def youtube_embed_url(self):
        """Converts standard YouTube watch, share, or short URLs into an embeddable URL."""
        if not self.youtube_video_url:
            return None
        match = re.search(r"(?:youtu\.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]{11})", self.youtube_video_url)
        if match:
            return f"https://www.youtube-nocookie.com/embed/{match.group(1)}"
        return None

    def increment_visit_count(self):
        Post.objects.filter(id=self.id).update(visit_count=models.F("visit_count") + 1)

    def calculate_reading_time(self):
        # Clean HTML tags to estimate reading speed (~200 wpm)
        clean_text = re.sub(r"<[^>]+>", " ", self.content_html or "")
        words = len(clean_text.split())
        return max(1, math.ceil(words / 200))

    def save(self, *args, **kwargs):
        # Generate slug if empty
        if not self.slug:
            base_slug = slugify(self.title) or "story"
            slug = base_slug
            counter = 1
            while Post.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        # Calculate read time automatically
        self.reading_time_minutes = self.calculate_reading_time()

        # Manage published_at timestamp
        if self.status == self.Status.PUBLISHED and self.is_approved and not self.published_at:
            self.published_at = timezone.now()

        super().save(*args, **kwargs)


class PostMediaAsset(models.Model):
    """Stores uploaded inline images inserted dynamically into block authoring."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="uploaded_media")
    post = models.ForeignKey(Post, on_delete=models.SET_NULL, null=True, blank=True, related_name="inline_assets")
    image = models.ImageField(upload_to="posts/content/%Y/%m/")
    caption = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("post media asset")
        verbose_name_plural = _("post media assets")
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"Asset #{self.id} by @{self.user.username}"