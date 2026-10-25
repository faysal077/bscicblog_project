from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    # Full Notifications Page
    path("", views.notification_list, name="list"),

    # Polling & Dropdown Endpoints
    path("api/unread-count/", views.unread_count_api, name="unread_count"),
    path("api/dropdown/", views.dropdown_notifications_api, name="dropdown_api"),

    # Status State Controls
    path("api/<int:notification_id>/read/", views.mark_as_read, name="mark_as_read"),
    path("api/mark-all-read/", views.mark_all_as_read, name="mark_all_as_read"),
]