from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from .models import Publication, PublicationMember

User = get_user_model()


class PublicationForm(forms.ModelForm):
    """Form to create and update publications/portals."""

    class Meta:
        model = Publication
        fields = [
            "name",
            "tagline",
            "description",
            "logo",
            "banner_image",
            "is_official",
        ]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control form-control-lg",
                "placeholder": "e.g., BSCIC Agro & Food Processing Hub",
            }),
            "tagline": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "A brief catchphrase or mission statement",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Comprehensive overview of the publication...",
            }),
            "logo": forms.FileInput(attrs={"class": "form-control"}),
            "banner_image": forms.FileInput(attrs={"class": "form-control"}),
            "is_official": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Restrict 'is_official' toggle strictly to Super Admins & BSCIC Officers
        if user and not user.is_officer:
            self.fields["is_official"].disabled = True
            self.fields["is_official"].widget = forms.HiddenInput()

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if len(name) < 3:
            raise ValidationError("Publication name must be at least 3 characters long.")

        qs = Publication.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("A publication with this name already exists.")
        return name

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.slug:
            base_slug = slugify(instance.name)
            slug = base_slug
            counter = 1
            while Publication.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            instance.slug = slug

        if commit:
            instance.save()
        return instance


class PublicationMemberForm(forms.ModelForm):
    """Form to add or modify editorial team members in a publication."""

    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Select an active contributor, editor, or officer.",
    )

    class Meta:
        model = PublicationMember
        fields = ["user", "role"]
        widgets = {
            "role": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = User.objects.filter(
            is_active=True,
            role__in=[
                User.Role.SUPER_ADMIN,
                User.Role.BSCIC_OFFICER,
                User.Role.EDITOR,
                User.Role.WRITER,
            ],
        ).order_by("full_name", "username")

    def clean_role(self):
        role = self.cleaned_data.get("role")
        if role not in [PublicationMember.Role.OWNER, PublicationMember.Role.EDITOR, PublicationMember.Role.WRITER]:
            raise ValidationError("Invalid editorial role selected.")
        return role