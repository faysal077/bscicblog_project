from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

User = get_user_model()


class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"class": "form-control bg-light border-0", "placeholder": "••••••••"}),
        min_length=8,
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={"class": "form-control bg-light border-0", "placeholder": "••••••••"}),
    )

    class Meta:
        model = User
        fields = ["email", "username", "full_name"]
        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-control bg-light border-0", "placeholder": "name@example.com"}),
            "username": forms.TextInput(attrs={"class": "form-control bg-light border-0", "placeholder": "username"}),
            "full_name": forms.TextInput(attrs={"class": "form-control bg-light border-0", "placeholder": "Full Name"}),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account registered with this email already exists.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get("username", "").strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("This username is already taken.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.role = User.Role.WRITER  # Standard registered accounts can write/draft
        if commit:
            user.save()
        return user


class EmailLoginForm(AuthenticationForm):
    """Custom login validating credentials against the unique email address."""
    username = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={"class": "form-control bg-light border-0", "placeholder": "name@bscic.gov.bd", "autofocus": True}),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"class": "form-control bg-light border-0", "placeholder": "••••••••"}),
    )

    def clean(self):
        email = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if email and password:
            self.user_cache = authenticate(self.request, username=email, password=password)
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data


class ProfileUpdateForm(forms.ModelForm):
    """Self-serve profile management form."""
    class Meta:
        model = User
        fields = ["full_name", "designation", "department", "bio", "website_url", "avatar"]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "designation": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Promotion Officer"}),
            "department": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., BSCIC Industrial Estate, Tongi"}),
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Share your expertise..."}),
            "website_url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://..."}),
            "avatar": forms.FileInput(attrs={"class": "form-control"}),
        }