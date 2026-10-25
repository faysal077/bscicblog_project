from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    # Django Built-in Admin Interface (Secondary backup)
    path("admin/", admin.site.urls),

    # Accounts & User Frontend Dashboard
    path("accounts/", include("accounts.urls")),

    # Dedicated Frontend Admin Control Panel
    path("dashboard/", include("dashboard.urls")),

    

    # Social Interactions (Claps, Comments, Subscriptions, Bookmarks)
    path("interactions/", include("interactions.urls")),

    # Analytics Trackers & Metric Endpoints
    path("analytics/", include("analytics.urls")),

    # Notifications Engine
    path("notifications/", include("notifications.urls")),

    # Posts & Reader Feeds (Mapped to Root)
    path("", include("posts.urls")),
]

# Serve media files locally during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom Error Views
handler403 = "django.views.defaults.permission_denied"
handler404 = "django.views.defaults.page_not_found"