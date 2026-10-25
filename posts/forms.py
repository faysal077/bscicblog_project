from django import forms
from django.utils.text import slugify
from django.core.exceptions import ValidationError

from .models import Post, Tag, Category
from publications.models import Publication


class PostForm(forms.ModelForm):
    tags_input = forms.CharField(
        label="Tags",
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g., Handloom, Agro, SME, Loan (comma separated)"
        }),
        help_text="Separate tags with commas."
    )

    class Meta:
        model = Post
        fields = [
            "title",
            "subtitle",
            "category",
            "publication",
            "content_html",
            "featured_image",
            "featured_image_caption",
            "featured_image_alt",
            "youtube_video_url",
            "status",
            "visibility",
            "meta_title",
            "meta_description",
        ]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control form-control-lg border-0 fw-bold px-0",
                "placeholder": "Title"
            }),
            "subtitle": forms.TextInput(attrs={
                "class": "form-control border-0 text-muted fs-5 px-0",
                "placeholder": "Write a subtitle or lead paragraph..."
            }),
            "category": forms.Select(attrs={"class": "form-select"}),
            "publication": forms.Select(attrs={"class": "form-select"}),
            "content_html": forms.Textarea(attrs={
                "class": "form-control border p-3 rounded",
                "rows": 18,
                "placeholder": "Tell your story... Insert paragraphs, bullet points, numbered lists, inline images, or video links."
            }),
            "featured_image": forms.FileInput(attrs={"class": "form-control"}),
            "featured_image_caption": forms.TextInput(attrs={"class": "form-control", "placeholder": "Image caption / source credit"}),
            "featured_image_alt": forms.TextInput(attrs={"class": "form-control", "placeholder": "Descriptive text for accessibility"}),
            "youtube_video_url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://www.youtube.com/watch?v=..."}),
            "status": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "visibility": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "meta_title": forms.TextInput(attrs={"class": "form-control", "placeholder": "SEO Title (optional)"}),
            "meta_description": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "SEO Meta Description (optional)"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Populate comma-separated tags on edit
        if self.instance.pk:
            self.fields["tags_input"].initial = ", ".join(t.name for t in self.instance.tags.all())

        # Restrict publications to those the user has writing access to
        if user and not user.is_super_admin:
            self.fields["publication"].queryset = Publication.objects.filter(
                members__user=user
            ).distinct()

    def clean_title(self):
        title = self.cleaned_data.get("title", "").strip()
        if len(title) < 5:
            raise ValidationError("Story title must be at least 5 characters long.")
        return title

    def save(self, commit=True):
        instance = super().save(commit=False)

        if commit:
            instance.save()
            # Process comma-separated tags
            raw_tags = self.cleaned_data.get("tags_input", "")
            if raw_tags:
                tag_names = [t.strip() for t in raw_tags.split(",") if t.strip()]
                tag_objs = []
                for name in tag_names[:5]:  # Allow max 5 tags
                    tag_obj, _ = Tag.objects.get_or_create(
                        name__iexact=name,
                        defaults={"name": name, "slug": slugify(name)}
                    )
                    tag_objs.append(tag_obj)
                instance.tags.set(tag_objs)
            else:
                instance.tags.clear()

        return instance