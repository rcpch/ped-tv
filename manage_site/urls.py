from django.urls import path
from . import views

app_name = "manage"

urlpatterns = [
    path("", views.ManageHomeView.as_view(), name="home"),
    # Providers
    path("providers/", views.ProviderListView.as_view(), name="provider-list"),
    path("providers/add/", views.ProviderCreateView.as_view(), name="provider-add"),
    path("providers/<int:pk>/edit/", views.ProviderUpdateView.as_view(), name="provider-edit"),
    path("providers/<int:pk>/delete/", views.ProviderDeleteView.as_view(), name="provider-delete"),
    # Playlists
    path("playlists/new/", views.PlaylistCreateView.as_view(), name="playlist-create"),
    path("playlists/<int:pk>/", views.PlaylistEditView.as_view(), name="playlist-edit"),
    # Media
    path("media/upload/", views.MediaUploadView.as_view(), name="media-upload"),
    path("media/for-provider/", views.MediaForProviderView.as_view(), name="media-for-provider"),
]
