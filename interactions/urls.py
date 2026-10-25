from django.urls import path
from . import views

app_name = "interactions"

urlpatterns = [
    # Clapping Endpoints
    path("posts/<int:post_id>/clap/", views.post_clap_toggle, name="post_clap"),
    path("comments/<int:comment_id>/clap/", views.comment_clap_toggle, name="comment_clap"),

    # Comment Submission
    path("posts/<int:post_id>/comment/", views.add_comment, name="add_comment"),

    # Bookmarks & Reading Lists
    path("posts/<int:post_id>/bookmark/", views.quick_bookmark_toggle, name="quick_bookmark"),
    path("library/", views.reading_lists_dashboard, name="reading_lists"),
    path("library/create/", views.create_reading_list, name="create_reading_list"),
    path("library/<int:list_id>/", views.reading_list_detail, name="reading_list_detail"),
    path("bookmarks/<int:item_id>/delete/", views.remove_bookmark_item, name="remove_bookmark_item"),

    # Social Follow Graph
    path("follow/toggle/", views.toggle_follow, name="toggle_follow"),

    # Newsletter Subscription
    path("subscribe/", views.subscribe_newsletter, name="subscribe"),
]