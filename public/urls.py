from django.urls import path
from . import views

urlpatterns = [
    path("", views.FrontPageView.as_view(), name="front-page"),
    path("playlist/<slug:slug>/", views.PlaylistPageView.as_view(), name="playlist"),
]
