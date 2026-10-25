from django.shortcuts import render

# Create your views here.
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from accounts.permissions import OfficerRequiredMixin
from posts.models import Post
from .forms import PublicationForm, PublicationMemberForm
from .models import Publication, PublicationMember


class PublicationListView(ListView):
    """Lists all active publications and official BSCIC hubs."""

    model = Publication
    template_name = "publications/publication_list.html"
    context_object_name = "publications"
    paginate_by = 12

    def get_queryset(self):
        return (
            Publication.objects.annotate(
                total_stories=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED, posts__is_approved=True)),
                total_followers=Count("followers"),
            )
            .order_by("-is_official", "-total_stories", "name")
        )


class PublicationDetailView(DetailView):
    """Public landing page of a publication displaying published stories and staff."""

    model = Publication
    template_name = "publications/publication_detail.html"
    context_object_name = "publication"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pub = self.object

        # Published stories inside this publication
        context["stories"] = (
            Post.objects.filter(
                publication=pub,
                status=Post.Status.PUBLISHED,
                is_approved=True,
                visibility=Post.Visibility.PUBLIC,
            )
            .select_related("author")
            .order_by("-published_at")[:15]
        )

        # Editorial team members
        context["editorial_members"] = (
            PublicationMember.objects.filter(publication=pub)
            .select_related("user")
            .order_by("role", "joined_at")
        )

        # Membership status of the logged-in user
        user = self.request.user
        context["user_role"] = None
        context["can_manage"] = False
        if user.is_authenticated:
            member = PublicationMember.objects.filter(publication=pub, user=user).first()
            if member:
                context["user_role"] = member.role
            if (
                user.is_super_admin
                or pub.owner == user
                or (member and member.role in [PublicationMember.Role.OWNER, PublicationMember.Role.EDITOR])
            ):
                context["can_manage"] = True

        return context


class PublicationCreateView(LoginRequiredMixin, OfficerRequiredMixin, CreateView):
    """Creation of official hubs restricted to BSCIC Officers and Super Admins."""

    model = Publication
    form_class = PublicationForm
    template_name = "publications/publication_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.owner = self.request.user
        if self.request.user.is_officer:
            form.instance.is_official = True

        publication = form.save()

        # Add creator as OWNER in the PublicationMember table
        PublicationMember.objects.create(
            publication=publication,
            user=self.request.user,
            role=PublicationMember.Role.OWNER,
        )

        messages.success(self.request, f'Publication "{publication.name}" created successfully.')
        return redirect("publications:publication_detail", slug=publication.slug)


class PublicationUpdateView(LoginRequiredMixin, UpdateView):
    """Update publication settings; restricted to owner or editors."""

    model = Publication
    form_class = PublicationForm
    template_name = "publications/publication_form.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def dispatch(self, request, *args, **kwargs):
        pub = self.get_object()
        user = request.user
        if not user.is_authenticated:
            return redirect("accounts:login")

        is_editor = PublicationMember.objects.filter(
            publication=pub,
            user=user,
            role__in=[PublicationMember.Role.OWNER, PublicationMember.Role.EDITOR],
        ).exists()

        if not (user.is_super_admin or pub.owner == user or is_editor):
            raise PermissionDenied("You do not have administrative clearance to edit this publication.")
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        messages.success(self.request, "Publication profile updated.")
        return reverse("publications:publication_detail", kwargs={"slug": self.object.slug})


@login_required
def manage_members_view(request, slug):
    """Manage publication staff, add members, change roles, and remove writers."""
    publication = get_object_or_404(Publication, slug=slug)
    user = request.user

    is_manager = (
        user.is_super_admin
        or publication.owner == user
        or PublicationMember.objects.filter(
            publication=publication,
            user=user,
            role__in=[PublicationMember.Role.OWNER, PublicationMember.Role.EDITOR],
        ).exists()
    )

    if not is_manager:
        raise PermissionDenied("Only publication editors and owners can manage members.")

    members = PublicationMember.objects.filter(publication=publication).select_related("user")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add_member":
            form = PublicationMemberForm(request.POST)
            if form.is_valid():
                target_user = form.cleaned_data["user"]
                role = form.cleaned_data["role"]

                member, created = PublicationMember.objects.get_or_create(
                    publication=publication,
                    user=target_user,
                    defaults={"role": role},
                )
                if not created:
                    member.role = role
                    member.save(update_fields=["role"])
                    messages.info(request, f"Updated role for {target_user.username} to {role}.")
                else:
                    messages.success(request, f"Added {target_user.username} as {role}.")
                return redirect("publications:manage_members", slug=publication.slug)

        elif action == "remove_member":
            member_id = request.POST.get("member_id")
            member_to_remove = get_object_or_404(PublicationMember, id=member_id, publication=publication)

            if member_to_remove.user == publication.owner and not user.is_super_admin:
                messages.error(request, "Cannot remove the primary publication owner.")
            else:
                member_to_remove.delete()
                messages.success(request, f"Removed {member_to_remove.user.username} from the publication.")
            return redirect("publications:manage_members", slug=publication.slug)

    else:
        form = PublicationMemberForm()

    context = {
        "publication": publication,
        "members": members,
        "form": form,
    }
    return render(request, "publications/publication_members.html", context)