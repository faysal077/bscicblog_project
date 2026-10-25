from django.urls import path
from . import views

app_name = "publications"

urlpatterns = [
    path("", views.PublicationListView.as_view(), name="publication_list"),
    path("new/", views.PublicationCreateView.as_view(), name="publication_create"),
    path("<slug:slug>/", views.PublicationDetailView.as_view(), name="publication_detail"),
    path("<slug:slug>/edit/", views.PublicationUpdateView.as_view(), name="publication_update"),
    path("<slug:slug>/members/", views.manage_members_view, name="manage_members"),
]