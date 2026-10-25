from django.shortcuts import render

# Create your views here.
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib import messages
from django.db.models import Sum, Count, Q

from posts.models import Post, Category
from publications.models import Publication
from accounts.models import User
from .models import (
    PostClap,
    Comment,
    CommentClap,
    ReadingList,
    BookmarkItem,
    Subscriber,
    Follow
)
from .forms import ReadingListForm, NewsletterSubscriptionForm


@login_required
@require_POST
def post_clap_toggle(request, post_id):
    """Adds claps up to a personal ceiling of 50 claps per post."""
    post = get_object_or_404(Post, id=post_id)
    try:
        data = json.loads(request.body)
        claps_to_add = int(data.get("claps_to_add", 1))
    except (ValueError, TypeError, json.JSONDecodeError):
        claps_to_add = 1

    clap_obj, created = PostClap.objects.get_or_create(
        post=post,
        user=request.user,
        defaults={"count": 0}
    )

    if clap_obj.count + claps_to_add > 50:
        claps_to_add = max(0, 50 - clap_obj.count)

    clap_obj.count += claps_to_add
    clap_obj.save()

    total_claps = post.claps.aggregate(Sum("count"))["count__sum"] or 0

    return JsonResponse({
        "success": True,
        "user_claps": clap_obj.count,
        "total_post_claps": total_claps
    })


@login_required
@require_POST
def add_comment(request, post_id):
    """Appends a new top-level comment or nested reply."""
    post = get_object_or_404(Post, id=post_id)
    text = request.POST.get("text") or request.POST.get("content")
    parent_id = request.POST.get("parent_id")

    if not text or not text.strip():
        messages.error(request, "Comment cannot be empty.")
        return redirect(request.META.get("HTTP_REFERER", "posts:post_list"))

    parent_comment = None
    if parent_id:
        parent_comment = get_object_or_404(Comment, id=parent_id, post=post)

    Comment.objects.create(
        post=post,
        author=request.user,
        parent=parent_comment,
        content=text.strip()
    )
    messages.success(request, "Your response has been published.")
    return redirect(request.META.get("HTTP_REFERER", "posts:post_list"))


@login_required
@require_POST
def comment_clap_toggle(request, comment_id):
    """Claps for an individual comment response."""
    comment = get_object_or_404(Comment, id=comment_id)
    clap_obj, created = CommentClap.objects.get_or_create(
        comment=comment,
        user=request.user,
        defaults={"count": 0}
    )
    clap_obj.count += 1
    clap_obj.save()

    total_claps = comment.claps.aggregate(Sum("count"))["count__sum"] or 0
    return JsonResponse({"success": True, "total_comment_claps": total_claps})


@login_required
@require_POST
def quick_bookmark_toggle(request, post_id):
    """Toggles bookmarking into the user's default 'Quick Reads' list."""
    post = get_object_or_404(Post, id=post_id)
    
    # Fetch or generate user's default reading list
    reading_list, _ = ReadingList.objects.get_or_create(
        user=request.user,
        title="Saved Stories",
        defaults={"description": "Default reading list", "is_private": True}
    )

    bookmark_item = BookmarkItem.objects.filter(reading_list=reading_list, post=post).first()
    if bookmark_item:
        bookmark_item.delete()
        bookmarked = False
    else:
        BookmarkItem.objects.create(reading_list=reading_list, post=post)
        bookmarked = True

    return JsonResponse({"success": True, "bookmarked": bookmarked})


@login_required
def reading_lists_dashboard(request):
    """Library view displaying all reading lists owned by the current user."""
    user_lists = (
        ReadingList.objects.filter(user=request.user)
        .annotate(total_items=Count("items"))
        .order_by("-created_at")
    )
    return render(request, "interactions/reading_lists.html", {"reading_lists": user_lists})


@login_required
def reading_list_detail(request, list_id):
    """Detailed view of an individual reading list and its bookmarked posts."""
    reading_list = get_object_or_404(ReadingList, id=list_id)

    if reading_list.is_private and reading_list.user != request.user:
        messages.error(request, "This reading list is marked as private by its curator.")
        return redirect("interactions:reading_lists")

    bookmark_items = (
        reading_list.items.select_related("post", "post__author", "post__category")
        .order_by("-saved_at")
    )

    return render(request, "interactions/reading_list_detail.html", {
        "reading_list": reading_list,
        "bookmark_items": bookmark_items
    })


@login_required
@require_POST
def create_reading_list(request):
    """Modal/Form endpoint to create a customized reading collection."""
    form = ReadingListForm(request.POST)
    if form.is_valid():
        rlist = form.save(commit=False)
        rlist.user = request.user
        rlist.save()
        messages.success(request, f'Collection "{rlist.title}" created.')
    else:
        messages.error(request, "Could not create list. Please verify the title length.")
    return redirect("interactions:reading_lists")


@login_required
@require_POST
def remove_bookmark_item(request, item_id):
    """Removes a specific story from a reading collection."""
    item = get_object_or_404(BookmarkItem, id=item_id, reading_list__user=request.user)
    item.delete()
    return JsonResponse({"success": True})


@login_required
@require_POST
def toggle_follow(request):
    """Follows or unfollows an author or publication portal."""
    try:
        data = json.loads(request.body)
        target_type = data.get("target_type")
        target_id = data.get("target_id")
    except (ValueError, TypeError, json.JSONDecodeError):
        return HttpResponseBadRequest("Invalid payload")

    if target_type == "author":
        target_author = get_object_or_404(User, id=target_id)
        if target_author == request.user:
            return JsonResponse({"success": False, "message": "You cannot follow yourself."}, status=400)

        follow_rel = Follow.objects.filter(user=request.user, author=target_author).first()
        if follow_rel:
            follow_rel.delete()
            following = False
        else:
            Follow.objects.create(user=request.user, author=target_author)
            following = True

    elif target_type == "publication":
        target_pub = get_object_or_404(Publication, id=target_id)
        follow_rel = Follow.objects.filter(user=request.user, publication=target_pub).first()
        if follow_rel:
            follow_rel.delete()
            following = False
        else:
            Follow.objects.create(user=request.user, publication=target_pub)
            following = True
    else:
        return HttpResponseBadRequest("Unsupported follow target")

    return JsonResponse({"success": True, "following": following})


@require_POST
def subscribe_newsletter(request):
    """Global newsletter subscription collection endpoint."""
    form = NewsletterSubscriptionForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Thank you! You are subscribed to official BSCIC bulletins.")
    else:
        error_msg = form.errors.get("email", ["Invalid email"])[0]
        messages.info(request, error_msg)

    return redirect(request.META.get("HTTP_REFERER", "/"))