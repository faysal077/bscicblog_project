from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class Publication(models.Model):
    name = models.CharField(_("publication name"), max_length=150, unique=True)
    slug = models.SlugField(_("slug"), max_length=170, unique=True, db_index=True)
    tagline = models.CharField(_("tagline / catchphrase"), max_length=255, blank=True)
    description = models.TextField(_("description"), blank=True)

    logo = models.ImageField(
        _("publication logo"),
        upload_to="publications/logos/%Y/%m/",
        null=True,
        blank=True,
    )
    banner_image = models.ImageField(
        _("banner image"),
        upload_to="publications/banners/%Y/%m/",
        null=True,
        blank=True,
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_publications",
        verbose_name=_("primary owner"),
    )

    is_official = models.BooleanField(
        _("official BSCIC publication"),
        default=False,
        help_text=_("Designates whether this hub represents an official BSCIC department/directorate."),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("publication")
        verbose_name_plural = _("publications")
        ordering = ["-is_official", "name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("publications:publication_detail", kwargs={"slug": self.slug})

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "publication"
            slug = base_slug
            counter = 1
            while Publication.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class PublicationMember(models.Model):
    class Role(models.TextChoices):
        OWNER = "OWNER", _("Owner")
        EDITOR = "EDITOR", _("Editor")
        WRITER = "WRITER", _("Writer / Contributor")

    publication = models.ForeignKey(
        Publication,
        on_delete=models.CASCADE,
        related_name="members",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="publication_memberships",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.WRITER,
        db_index=True,
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("publication member")
        verbose_name_plural = _("publication members")
        unique_together = ("publication", "user")
        indexes = [
            models.Index(fields=["publication", "role"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()} at {self.publication.name}"