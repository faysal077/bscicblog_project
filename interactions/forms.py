from django import forms
from django.core.exceptions import ValidationError

from .models import Comment, ReadingList, Subscriber


class CommentForm(forms.ModelForm):
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 3,
            "placeholder": "What are your thoughts on this story or policy?"
        }),
        max_length=1500
    )

    class Meta:
        model = Comment
        fields = ["content"]


class ReadingListForm(forms.ModelForm):
    class Meta:
        model = ReadingList
        fields = ["title", "description", "is_private"]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g., SME Credit & Handloom Research"
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 2,
                "placeholder": "Brief context for this collection..."
            }),
            "is_private": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class NewsletterSubscriptionForm(forms.ModelForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "Enter your work or personal email address...",
            "required": True
        })
    )

    class Meta:
        model = Subscriber
        fields = ["email"]

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if Subscriber.objects.filter(email=email).exists():
            raise ValidationError("You are already subscribed to the BSCIC updates bulletin.")
        return email