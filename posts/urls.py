from django.urls import path
from . import views

app_name = "posts"

urlpatterns = [
    # Story Feeds & Exploration
    path("", views.PostListView.as_view(), name="post_list"),
    path("search/", views.search_results_view, name="search"),
    
    # Authoring & Block Media Tools
    path("new/", views.post_create, name="post_create"),
    path("api/upload-image/", views.upload_inline_image, name="upload_inline_image"),
    
    # Categorizations & Taxonomy
    path("category/<slug:slug>/", views.category_posts_view, name="category_posts"),
    path("tag/<slug:slug>/", views.tag_posts_view, name="tag_posts"),

    # Story Details & Edit (Kept at bottom to prevent slug collisions)
    path("<slug:slug>/", views.PostDetailView.as_view(), name="post_detail"),
    path("<slug:slug>/edit/", views.post_edit, name="post_edit"),
]