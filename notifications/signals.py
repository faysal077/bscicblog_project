from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse

from interactions.models import PostClap, Comment, Follow
from posts.models import Post
from .models import Notification


@receiver(post_save, sender=PostClap)
def notify_post_clap(sender, instance, created, **kwargs):
    """Notify post author when another member claps for their story."""
    post = instance.post
    if instance.user != post.author:
        # Avoid duplicate alert records; update existing or create
        Notification.objects.get_or_create(
            recipient=post.author,
            actor=instance.user,
            verb=Notification.Verb.CLAP,
            target_post=post,
            defaults={"target_url": post.get_absolute_url()}
        )


@receiver(post_save, sender=Comment)
def notify_comment_activity(sender, instance, created, **kwargs):
    """Notify story author or parent comment author when a comment/reply is published."""
    if not created or instance.is_deleted:
        return

    post = instance.post

    # If it is a reply to an existing comment
    if instance.parent and instance.parent.author != instance.author:
        Notification.objects.create(
            recipient=instance.parent.author,
            actor=instance.author,
            verb=Notification.Verb.REPLY,
            target_post=post,
            target_url=f"{post.get_absolute_url()}#comment-{instance.id}"
        )
    # If it is a top-level comment on someone else's post
    elif instance.author != post.author:
        Notification.objects.create(
            recipient=post.author,
            actor=instance.author,
            verb=Notification.Verb.COMMENT,
            target_post=post,
            target_url=f"{post.get_absolute_url()}#comment-{instance.id}"
        )


@receiver(post_save, sender=Follow)
def notify_new_follower(sender, instance, created, **kwargs):
    """Notify author when a user follows their profile."""
    if created and instance.author and instance.user != instance.author:
        profile_url = reverse("accounts:profile_detail", kwargs={"username": instance.user.username})
        Notification.objects.create(
            recipient=instance.author,
            actor=instance.user,
            verb=Notification.Verb.FOLLOW,
            target_url=profile_url
        )


@receiver(post_save, sender=Post)
def notify_post_status_change(sender, instance, **kwargs):
    """Notify author when an admin/officer approves or features their submitted draft."""
    if instance.is_approved and instance.status == Post.Status.PUBLISHED:
        # Check if an approval notification was already issued
        exists = Notification.objects.filter(
            recipient=instance.author,
            verb=Notification.Verb.POST_APPROVED,
            target_post=instance
        ).exists()

        if not exists:
            Notification.objects.create(
                recipient=instance.author,
                actor=instance.author,
                verb=Notification.Verb.POST_APPROVED,
                target_post=instance,
                target_url=instance.get_absolute_url()
            )