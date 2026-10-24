from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    # Main Admin KPI Overview
    path("", views.admin_overview, name="overview"),

    # Post Management & Moderation
    path("posts/", views.manage_posts, name="manage_posts"),
    path("posts/<int:post_id>/approve/", views.approve_post, name="approve_post"),
    path("posts/<int:post_id>/feature/", views.toggle_feature_post, name="toggle_feature_post"),
    path("posts/<int:post_id>/edit/", views.edit_post_admin, name="edit_post"),
    path("posts/<int:post_id>/delete/", views.delete_post_admin, name="delete_post"),

    # Category Management
    path("categories/", views.manage_categories, name="manage_categories"),
    path("categories/<int:category_id>/edit/", views.edit_category, name="edit_category"),
    path("categories/<int:category_id>/delete/", views.delete_category, name="delete_category"),

    # User Management
    path("users/", views.manage_users, name="manage_users"),
    path("users/<int:user_id>/edit/", views.edit_user, name="edit_user"),
    path("users/<int:user_id>/delete/", views.delete_user_admin, name="delete_user"),
]