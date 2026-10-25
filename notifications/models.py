from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from posts.models import Post


class Notification(models.Model):
    class Verb(models.TextChoices):
        CLAP = "clap", _("clapped for your story")
        COMMENT = "comment", _("commented on your story")
        REPLY = "reply", _("replied to your comment")
        FOLLOW = "follow", _("started following you")
        POST_APPROVED = "post_approved", _("Your story was approved and published")
        POST_FEATURED = "post_featured", _("Your story was highlighted as Featured")

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("recipient")
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_notifications",
        verbose_name=_("actor")
    )
    verb = models.CharField(_("action verb"), max_length=30, choices=Verb.choices)
    
    target_post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications"
    )
    target_url = models.CharField(_("target URL"), max_length=255, blank=True)
    
    is_read = models.BooleanField(_("is read"), default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("notification")
        verbose_name_plural = _("notifications")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
        ]

    def __str__(self):
        return f"{self.actor.username} {self.get_verb_display()} -> {self.recipient.username}"

    def save(self, *args, **kwargs):
        if not self.target_url and self.target_post:
            self.target_url = self.target_post.get_absolute_url()
        super().save(*args, **kwargs)