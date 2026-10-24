from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    # Authentication Endpoints
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),

    # Self-Serve User Frontend Dashboard & Story Controls
    path("dashboard/", views.user_dashboard, name="user_dashboard"),
    path("dashboard/posts/<int:post_id>/toggle-visibility/", views.toggle_post_visibility, name="toggle_post_visibility"),
    path("dashboard/posts/<int:post_id>/delete/", views.delete_post_user, name="delete_post_user"),

    # Profile & Identity
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    path("profile/<str:username>/", views.profile_detail, name="profile_detail"),

    # Institutional Staff Directory
    path("directory/", views.internal_directory, name="internal_directory"),
]