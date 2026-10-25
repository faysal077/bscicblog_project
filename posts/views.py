from django.shortcuts import render

# Create your views here.
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db.models import Count, Q, F

from accounts.permissions import WriterRequiredMixin
from .models import Post, Tag, Category, PostMediaAsset
from .forms import PostForm


class PostListView(ListView):
    """The central homepage / magazine feed."""
    model = Post
    template_name = "posts/post_list.html"
    context_object_name = "posts"
    paginate_by = 10

    def get_queryset(self):
        # Base filter: Only live approved stories visible to the public
        qs = (
            Post.objects.filter(
                status=Post.Status.PUBLISHED,
                is_approved=True,
                visibility=Post.Visibility.PUBLIC
            )
            .select_related("author", "category", "publication")
            .prefetch_related("tags")
        )

        sort_param = self.request.GET.get("sort")
        if sort_param == "top_read":
            return qs.order_by("-visit_count", "-published_at")
        elif sort_param == "claps":
            return qs.annotate(clap_count=Count("claps")).order_by("-clap_count", "-published_at")
        return qs.order_by("-published_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Featured highlight posts for top carousel / cards
        context["featured_posts"] = (
            Post.objects.filter(
                status=Post.Status.PUBLISHED,
                is_approved=True,
                is_featured=True,
                visibility=Post.Visibility.PUBLIC
            )
            .select_related("author", "category")
            .order_by("-published_at")[:4]
        )

        # Categories ordered by highest count of published posts
        context["trending_categories"] = (
            Category.objects.annotate(
                total_posts=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED, posts__is_approved=True))
            )
            .order_by("-total_posts", "name")[:8]
        )

        context["current_sort"] = self.request.GET.get("sort", "recent")
        return context


class PostDetailView(DetailView):
    """Dedicated long-form reading view."""
    model = Post
    template_name = "posts/post_detail.html"
    context_object_name = "post"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)
        user = self.request.user

        # Access rule: Author, BSCIC Officer, and Super Admin can preview unapproved/draft stories
        can_preview = (
            user.is_authenticated and (
                user == obj.author or 
                user.is_super_admin or 
                user.is_officer
            )
        )
        if not can_preview:
            if obj.status != Post.Status.PUBLISHED or not obj.is_approved:
                raise PermissionDenied("This story is awaiting moderation or is kept in drafts.")

        # Increment visit counter on legitimate page loads
        obj.increment_visit_count()
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.object

        # Similar / related stories based on same category or author
        context["similar_posts"] = (
            Post.objects.filter(
                status=Post.Status.PUBLISHED,
                is_approved=True,
                visibility=Post.Visibility.PUBLIC
            )
            .filter(Q(category=post.category) | Q(author=post.author))
            .exclude(id=post.id)
            .select_related("author", "category")
            .order_by("-published_at")[:3]
        )
        return context


@login_required
def post_create(request):
    """Authoring canvas to write, upload inline media, and draft new stories."""
    if not request.user.can_write:
        raise PermissionDenied("You must hold contributor or officer privileges to publish stories.")

    if request.method == "POST":
        form = PostForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user

            # BSCIC Officers and Super Admins get auto-approval
            if request.user.is_officer:
                post.is_approved = True

            post.save()
            form.save_m2m()  # Saves tags

            if post.is_approved and post.status == Post.Status.PUBLISHED:
                messages.success(request, f'"{post.title}" is published live!')
                return redirect("posts:post_detail", slug=post.slug)
            else:
                messages.info(request, f'"{post.title}" saved. It will appear live once reviewed by moderators.')
                return redirect("accounts:user_dashboard")
    else:
        # Preselect publication if passed in query param
        initial_data = {}
        pub_id = request.GET.get("publication")
        if pub_id:
            initial_data["publication"] = pub_id
        form = PostForm(initial=initial_data, user=request.user)

    return render(request, "posts/post_form.html", {"form": form})


@login_required
def post_edit(request, slug):
    """Edit existing story canvas."""
    post = get_object_or_404(Post, slug=slug)

    # Permission check: Author or moderator
    if not (request.user == post.author or request.user.is_officer or request.user.is_super_admin):
        raise PermissionDenied("You are not permitted to edit this story.")

    if request.method == "POST":
        form = PostForm(request.POST, request.FILES, instance=post, user=request.user)
        if form.is_valid():
            post = form.save()
            messages.success(request, f'Changes saved for "{post.title}".')
            return redirect("posts:post_detail", slug=post.slug)
    else:
        form = PostForm(instance=post, user=request.user)

    return render(request, "posts/post_form.html", {"form": form, "post": post})


def tag_posts_view(request, slug):
    """Explore stories associated with a specific tag."""
    tag = get_object_or_404(Tag, slug=slug)
    posts = (
        Post.objects.filter(
            tags=tag,
            status=Post.Status.PUBLISHED,
            is_approved=True,
            visibility=Post.Visibility.PUBLIC
        )
        .select_related("author", "category")
        .order_by("-published_at")
    )
    return render(request, "posts/tag_posts.html", {"tag": tag, "posts": posts})


def category_posts_view(request, slug):
    """Dedicated single category hub by Featured, Popular, and Recent."""
    category = get_object_or_404(Category, slug=slug)
    base_qs = (
        Post.objects.filter(
            category=category,
            status=Post.Status.PUBLISHED,
            is_approved=True,
            visibility=Post.Visibility.PUBLIC
        )
        .select_related("author", "publication")
    )

    filter_type = request.GET.get("tab", "recent")
    if filter_type == "featured":
        posts = base_qs.filter(is_featured=True).order_by("-published_at")
    elif filter_type == "popular":
        posts = base_qs.order_by("-visit_count", "-published_at")
    else:
        posts = base_qs.order_by("-published_at")

    context = {
        "category": category,
        "posts": posts,
        "active_tab": filter_type,
        "total_category_stories": base_qs.count(),
    }
    return render(request, "interactions/category_detail.html", context)


def search_results_view(request):
    """Full-text discovery across titles, contents, authors, and tags."""
    query = request.GET.get("q", "").strip()
    results = []

    if query:
        results = (
            Post.objects.filter(
                status=Post.Status.PUBLISHED,
                is_approved=True,
                visibility=Post.Visibility.PUBLIC
            )
            .filter(
                Q(title__icontains=query) |
                Q(subtitle__icontains=query) |
                Q(content_html__icontains=query) |
                Q(tags__name__icontains=query) |
                Q(author__username__icontains=query) |
                Q(author__full_name__icontains=query)
            )
            .distinct()
            .select_related("author", "category")
            .order_by("-published_at")
        )

    return render(request, "posts/search_results.html", {"query": query, "results": results})


@login_required
@require_POST
def upload_inline_image(request):
    """Endpoint handling asynchronous inline image uploads for block authoring."""
    if "image" not in request.FILES:
        return JsonResponse({"success": False, "message": "No image file provided."}, status=400)

    image_file = request.FILES["image"]
    asset = PostMediaAsset.objects.create(
        user=request.user,
        image=image_file
    )

    return JsonResponse({
        "success": True,
        "file": {
            "url": asset.image.url,
            "id": asset.id
        }
    })