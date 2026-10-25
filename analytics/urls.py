from django.urls import path
from . import views

app_name = "analytics"

urlpatterns = [
    # Visual Analytics Dashboards
    path("dashboard/", views.analytics_dashboard, name="dashboard"),
    path("posts/<int:post_id>/", views.post_stats_detail, name="post_stats"),

    # Asynchronous Data Endpoints & Beacons
    path("posts/<int:post_id>/view/", views.record_post_view, name="record_view"),
    path("posts/<int:post_id>/read/", views.record_read_beacon, name="record_read"),
    path("posts/<int:post_id>/stats/", views.post_stats_api, name="post_stats_api"),
]