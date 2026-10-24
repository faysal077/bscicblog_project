from django.shortcuts import render

# Create your views here.
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model

from posts.models import Post, Category
from interactions.models import Comment, Subscriber
from .forms import (
    CategoryForm,
    AdminPostFeatureForm,
    AdminUserCreationForm,
    AdminUserEditForm,
)

User = get_user_model()


def admin_required(view_func):
    """Ensures only Super Admins, BSCIC Officers, or Staff can access dashboard controls."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        if not (request.user.is_super_admin or request.user.is_officer or request.user.is_staff):
            raise PermissionDenied("You do not have administrative clearance to access the executive dashboard.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


@login_required
@admin_required
def admin_overview(request):
    """Main administrative KPI dashboard showing pending review queues and aggregates."""
    pending_posts = (
        Post.objects.filter(is_approved=False)
        .select_related("author", "category")
        .order_by("-created_at")[:10]
    )

    recent_posts = (
        Post.objects.select_related("author", "category")
        .order_by("-created_at")[:10]
    )

    context = {
        "pending_posts": pending_posts,
        "recent_posts": recent_posts,
        "total_posts": Post.objects.count(),
        "pending_count": Post.objects.filter(is_approved=False).count(),
        "total_users": User.objects.count(),
        "total_categories": Category.objects.count(),
        "total_subscribers": Subscriber.objects.count(),
        "total_comments": Comment.objects.count(),
    }
    return render(request, "dashboard/index.html", context)


@login_required
@admin_required
def manage_posts(request):
    """View and filter posts across approvals, featured status, and publications."""
    status_filter = request.GET.get("status")
    approval_filter = request.GET.get("approved")
    category_filter = request.GET.get("category")
    search_query = request.GET.get("q", "").strip()

    posts = Post.objects.select_related("author", "category").order_by("-created_at")

    if status_filter:
        posts = posts.filter(status=status_filter)
    if approval_filter in ["true", "1"]:
        posts = posts.filter(is_approved=True)
    elif approval_filter in ["false", "0"]:
        posts = posts.filter(is_approved=False)
    if category_filter:
        posts = posts.filter(category__id=category_filter)
    if search_query:
        posts = posts.filter(
            Q(title__icontains=search_query) |
            Q(author__username__icontains=search_query) |
            Q(author__full_name__icontains=search_query)
        )

    paginator = Paginator(posts, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.all().order_by("name")

    context = {
        "page_obj": page_obj,
        "categories": categories,
        "search_query": search_query,
        "status_filter": status_filter,
        "approval_filter": approval_filter,
        "category_filter": category_filter,
    }
    return render(request, "dashboard/manage_posts.html", context)


@login_required
@admin_required
def approve_post(request, post_id):
    """Approves a submitted post and transitions its state to published."""
    post = get_object_or_404(Post, id=post_id)
    post.is_approved = True
    post.status = Post.Status.PUBLISHED
    post.save(update_fields=["is_approved", "status"])
    messages.success(request, f'Story "{post.title}" has been approved and published.')
    return redirect(request.META.get("HTTP_REFERER", "dashboard:manage_posts"))


@login_required
@admin_required
def toggle_feature_post(request, post_id):
    """Toggles whether an article appears on featured feeds."""
    post = get_object_or_404(Post, id=post_id)
    post.is_featured = not post.is_featured
    post.save(update_fields=["is_featured"])
    status = "featured" if post.is_featured else "unfeatured"
    messages.info(request, f'Story "{post.title}" marked as {status}.')
    return redirect(request.META.get("HTTP_REFERER", "dashboard:manage_posts"))


@login_required
@admin_required
def edit_post_admin(request, post_id):
    """Admin-level edit form to change categories, approval status, and feature flags."""
    post = get_object_or_404(Post, id=post_id)
    if request.method == "POST":
        form = AdminPostFeatureForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, f'Configuration updated for "{post.title}".')
            return redirect("dashboard:manage_posts")
    else:
        form = AdminPostFeatureForm(instance=post)

    return render(request, "dashboard/edit_post.html", {"form": form, "post": post})


@login_required
@admin_required
def delete_post_admin(request, post_id):
    """Admin endpoint to permanently delete a post."""
    post = get_object_or_404(Post, id=post_id)
    if request.method == "POST":
        title = post.title
        post.delete()
        messages.warning(request, f'Story "{title}" permanently deleted.')
        return redirect("dashboard:manage_posts")
    return render(request, "dashboard/confirm_post_delete.html", {"post": post})


@login_required
@admin_required
def manage_categories(request):
    """Lists existing categories with post counters and processes new category creation."""
    categories = (
        Category.objects.annotate(
            posts_count=Count("posts", filter=Q(posts__is_approved=True, posts__status=Post.Status.PUBLISHED))
        )
        .order_by("-posts_count", "name")
    )

    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            new_cat = form.save()
            messages.success(request, f'Category "{new_cat.name}" created successfully.')
            return redirect("dashboard:manage_categories")
    else:
        form = CategoryForm()

    context = {
        "categories": categories,
        "form": form,
    }
    return render(request, "dashboard/manage_categories.html", context)


@login_required
@admin_required
def edit_category(request, category_id):
    """Updates category name and description."""
    category = get_object_or_404(Category, id=category_id)
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Category "{category.name}" updated.')
            return redirect("dashboard:manage_categories")
    else:
        form = CategoryForm(instance=category)

    return render(request, "dashboard/edit_category.html", {"form": form, "category": category})


@login_required
@admin_required
def delete_category(request, category_id):
    """Deletes a category from the system."""
    category = get_object_or_404(Category, id=category_id)
    if request.method == "POST":
        cat_name = category.name
        category.delete()
        messages.warning(request, f'Category "{cat_name}" deleted.')
        return redirect("dashboard:manage_categories")
    return render(request, "dashboard/confirm_category_delete.html", {"category": category})


@login_required
@admin_required
def manage_users(request):
    """Lists registered users and handles onboarding new members directly from the frontend."""
    search_query = request.GET.get("q", "").strip()
    role_filter = request.GET.get("role")

    users = User.objects.all().order_by("-date_joined")

    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(full_name__icontains=search_query)
        )
    if role_filter:
        users = users.filter(role=role_filter)

    paginator = Paginator(users, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    if request.method == "POST":
        form = AdminUserCreationForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            messages.success(request, f"User account @{new_user.username} created.")
            return redirect("dashboard:manage_users")
    else:
        form = AdminUserCreationForm()

    context = {
        "page_obj": page_obj,
        "form": form,
        "search_query": search_query,
        "role_filter": role_filter,
        "role_choices": User.Role.choices,
    }
    return render(request, "dashboard/manage_users.html", context)


@login_required
@admin_required
def edit_user(request, user_id):
    """Edits permissions, clearances, and profile status of a member."""
    target_user = get_object_or_404(User, id=user_id)
    if request.method == "POST":
        form = AdminUserEditForm(request.POST, instance=target_user)
        if form.is_valid():
            form.save()
            messages.success(request, f"User @{target_user.username} profile updated.")
            return redirect("dashboard:manage_users")
    else:
        form = AdminUserEditForm(instance=target_user)

    return render(request, "dashboard/edit_user.html", {"form": form, "target_user": target_user})


@login_required
@admin_required
def delete_user_admin(request, user_id):
    """Permanently deletes a user account with safeguard against deleting self or superusers."""
    target_user = get_object_or_404(User, id=user_id)

    if target_user == request.user:
        messages.error(request, "You cannot delete your own active administrative account.")
        return redirect("dashboard:manage_users")

    if target_user.is_superuser and not request.user.is_superuser:
        raise PermissionDenied("Only superusers can remove another superuser account.")

    if request.method == "POST":
        username = target_user.username
        target_user.delete()
        messages.warning(request, f"Account @{username} has been permanently deleted.")
        return redirect("dashboard:manage_users")

    return render(request, "dashboard/confirm_user_delete.html", {"target_user": target_user})