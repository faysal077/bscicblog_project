from django import forms
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from posts.models import Category, Post

User = get_user_model()


class CategoryForm(forms.ModelForm):
    """Form to create and update categories."""
    class Meta:
        model = Category
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g., Agro & Food Processing"
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Brief description of the sector/category..."
            }),
        }

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if len(name) < 2:
            raise ValidationError("Category name must be at least 2 characters long.")
        qs = Category.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("A category with this name already exists.")
        return name

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.slug:
            base_slug = slugify(instance.name)
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            instance.slug = slug
        if commit:
            instance.save()
        return instance


class AdminPostFeatureForm(forms.ModelForm):
    """Allows administrators to change approval status, featured flag, and category."""
    class Meta:
        model = Post
        fields = ["category", "status", "is_approved", "is_featured"]
        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "is_approved": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_featured": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class AdminUserCreationForm(forms.ModelForm):
    """Allows administrators to onboard new users directly from the frontend."""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "••••••••"}),
        min_length=8
    )

    class Meta:
        model = User
        fields = ["username", "email", "full_name", "role", "designation", "department", "password"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control", "placeholder": "username"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "user@bscic.gov.bd"}),
            "full_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Full Name"}),
            "role": forms.Select(attrs={"class": "form-select"}),
            "designation": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Assistant Director"}),
            "department": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Planning Division"}),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email address already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class AdminUserEditForm(forms.ModelForm):
    """Allows administrators to update user roles, designations, and active states."""
    class Meta:
        model = User
        fields = ["full_name", "role", "designation", "department", "is_active", "is_verified"]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "role": forms.Select(attrs={"class": "form-select"}),
            "designation": forms.TextInput(attrs={"class": "form-control"}),
            "department": forms.TextInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_verified": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }