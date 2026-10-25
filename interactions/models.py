from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from posts.models import Post
from publications.models import Publication


class PostClap(models.Model):
    """Enables Medium-style multi-clapping (up to 50 claps per user)."""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="claps")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="post_claps")
    count = models.PositiveSmallIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("post clap")
        verbose_name_plural = _("post claps")
        unique_together = ("post", "user")

    def __str__(self):
        return f"{self.user.username} gave {self.count} claps on {self.post.title}"


class Comment(models.Model):
    """Supports nested comment trees (replies), moderation, and soft-delete states."""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments")
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies"
    )
    content = models.TextField(_("comment content"))
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("comment")
        verbose_name_plural = _("comments")
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author.username} on {self.post.title}"

    @property
    def total_claps_count(self):
        return self.claps.aggregate(models.Sum("count"))["count__sum"] or 0


class CommentClap(models.Model):
    """Clapping mechanism for individual comments."""
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="claps")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comment_claps")
    count = models.PositiveSmallIntegerField(default=1)

    class Meta:
        verbose_name = _("comment clap")
        verbose_name_plural = _("comment claps")
        unique_together = ("comment", "user")

    def __str__(self):
        return f"{self.user.username} clapped for comment #{self.comment.id}"


class ReadingList(models.Model):
    """Curated lists/folders created by users to save and organize articles."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reading_lists")
    title = models.CharField(_("list title"), max_length=150)
    description = models.CharField(_("description"), max_length=300, blank=True)
    is_private = models.BooleanField(_("private collection"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("reading list")
        verbose_name_plural = _("reading lists")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} (@{self.user.username})"


class BookmarkItem(models.Model):
    """M2M through-model linking a Post to a user's ReadingList."""
    reading_list = models.ForeignKey(ReadingList, on_delete=models.CASCADE, related_name="items")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="bookmarked_in")
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("bookmark item")
        verbose_name_plural = _("bookmark items")
        unique_together = ("reading_list", "post")
        ordering = ["-saved_at"]

    def __str__(self):
        return f"{self.post.title} in {self.reading_list.title}"


class Subscriber(models.Model):
    """Collects emails for industrial circulars and newsletters."""
    email = models.EmailField(_("email address"), unique=True)
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("newsletter subscriber")
        verbose_name_plural = _("newsletter subscribers")
        ordering = ["-subscribed_at"]

    def __str__(self):
        return self.email


class Follow(models.Model):
    """Follow graphs for authors and publication hubs."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="following_relations")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="followers_relations"
    )
    publication = models.ForeignKey(
        Publication,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="followers"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("follow")
        verbose_name_plural = _("follows")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "author"],
                condition=models.Q(author__isnull=False),
                name="unique_user_author_follow"
            ),
            models.UniqueConstraint(
                fields=["user", "publication"],
                condition=models.Q(publication__isnull=False),
                name="unique_user_publication_follow"
            ),
        ]

    def __str__(self):
        if self.author:
            return f"{self.user.username} follows @{self.author.username}"
        return f"{self.user.username} follows hub {self.publication.name}"