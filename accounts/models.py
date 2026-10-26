from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Custom manager where email is the unique identifier for auth."""

    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError(_("An email address is required."))
        if not username:
            raise ValueError(_("A unique username is required."))

        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.SUPER_ADMIN)
        extra_fields.setdefault("is_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email, username, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", _("Super Administrator")
        BSCIC_OFFICER = "bscic_officer", _("BSCIC Officer")
        EDITOR = "editor", _("Publication Editor")
        WRITER = "writer", _("Contributor")
        READER = "reader", _("General Reader")

    email = models.EmailField(_("email address"), unique=True)
    full_name = models.CharField(_("full name"), max_length=150, blank=True)
    role = models.CharField(
        _("system role"),
        max_length=20,
        choices=Role.choices,
        default=Role.READER,
        db_index=True,
    )
    
    # Professional & Directorate attributes
    designation = models.CharField(_("designation"), max_length=120, blank=True)
    department = models.CharField(_("department / estate"), max_length=150, blank=True)
    bio = models.TextField(_("biography"), max_length=500, blank=True)
    website_url = models.URLField(_("website or profile URL"), blank=True)
    
    avatar = models.ImageField(
        _("profile avatar"),
        upload_to="accounts/avatars/%Y/%m/",
        blank=True,
        null=True,
    )
    is_verified = models.BooleanField(
        _("verified official"),
        default=False,
        help_text=_("Designates whether this account displays an official BSCIC verified badge."),
    )

    objects = UserManager()

    REQUIRED_FIELDS = ["username"]
    USERNAME_FIELD = "email"

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["-date_joined"]

    def __str__(self):
        return self.full_name or self.username

    def get_absolute_url(self):
        return reverse("accounts:profile_detail", kwargs={"username": self.username})

    @property
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN or self.is_superuser

    @property
    def is_officer(self):
        return self.role in [self.Role.SUPER_ADMIN, self.Role.BSCIC_OFFICER] or self.is_superuser

    @property
    def can_publish(self):
        return self.role in [
            self.Role.SUPER_ADMIN,
            self.Role.BSCIC_OFFICER,
            self.Role.EDITOR,
        ] or self.is_superuser

    @property
    def can_write(self):
        return self.role in [
            self.Role.SUPER_ADMIN,
            self.Role.BSCIC_OFFICER,
            self.Role.EDITOR,
            self.Role.WRITER,
        ] or self.is_superuser