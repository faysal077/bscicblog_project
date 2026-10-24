from django.shortcuts import render

# Create your views here.
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from posts.models import Post
from .forms import EmailLoginForm, ProfileUpdateForm, UserRegistrationForm
from .models import User
from .permissions import role_required


def login_view(request):
    if request.user.is_authenticated:
        return redirect("posts:post_list")

    if request.method == "POST":
        form = EmailLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.full_name or user.username}!")
            next_url = request.GET.get("next") or "posts:post_list"
            return redirect(next_url)
    else:
        form = EmailLoginForm()

    return render(request, "accounts/login.html", {"form": form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect("posts:post_list")

    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully! Welcome to BSCIC Blog.")
            return redirect("posts:post_list")
    else:
        form = UserRegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("accounts:login")


@login_required
def user_dashboard(request):
    """User-facing personal control center for managing own authored stories."""
    user_posts = Post.objects.filter(author=request.user).order_by("-created_at")

    context = {
        "user_posts": user_posts,
        "total_posts": user_posts.count(),
        "published_count": user_posts.filter(status=Post.Status.PUBLISHED).count(),
        "hidden_count": user_posts.filter(status=Post.Status.DRAFT).count(),
        "pending_count": user_posts.filter(is_approved=False).count(),
    }
    return render(request, "accounts/dashboard.html", context)


@login_required
@require_POST
def toggle_post_visibility(request, post_id):
    """Toggle a story between Published and Draft (Show/Hide) from frontend."""
    post = get_object_or_404(Post, id=post_id, author=request.user)
    if post.status == Post.Status.PUBLISHED:
        post.status = Post.Status.DRAFT
        messages.info(request, f'"{post.title}" is now hidden (Draft).')
    else:
        post.status = Post.Status.PUBLISHED
        messages.success(request, f'"{post.title}" is now visible (Published).')
    post.save(update_fields=["status"])
    return redirect("accounts:user_dashboard")


@login_required
def delete_post_user(request, post_id):
    """Author-initiated story deletion from frontend dashboard."""
    post = get_object_or_404(Post, id=post_id, author=request.user)

    if request.method == "POST":
        title = post.title
        post.delete()
        messages.warning(request, f'Story "{title}" has been deleted.')
        return redirect("accounts:user_dashboard")

    return render(request, "dashboard/confirm_post_delete.html", {"post": post})


def profile_detail(request, username):
    """Public Medium-style writer profile displaying their stories and credentials."""
    profile_user = get_object_or_404(User, username=username)

    # Readers only see approved + published stories
    posts = Post.objects.filter(
        author=profile_user,
        status=Post.Status.PUBLISHED,
        is_approved=True,
    ).order_by("-published_at", "-created_at")

    context = {
        "profile_user": profile_user,
        "user_posts": posts,
    }
    return render(request, "accounts/profile_detail.html", context)


@login_required
def profile_edit(request):
    """Edit own profile details and avatar."""
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect("accounts:profile_detail", username=request.user.username)
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, "accounts/profile_edit.html", {"form": form})


@login_required
@role_required([User.Role.SUPER_ADMIN, User.Role.BSCIC_OFFICER, User.Role.EDITOR])
def internal_directory(request):
    """Restricted staff directory for BSCIC officers and publication editors."""
    officers = User.objects.filter(
        role__in=[User.Role.SUPER_ADMIN, User.Role.BSCIC_OFFICER, User.Role.EDITOR],
        is_active=True,
    ).order_by("full_name", "username")

    return render(request, "accounts/internal_directory.html", {"officers": officers})