from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from playlists.models import Playlist


class FrontPageView(TemplateView):
    template_name = "public/front_page.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        published = Playlist.objects.filter(status=Playlist.Status.PUBLISHED)
        main = published.filter(is_main=True).first()
        others = published.exclude(is_main=True).order_by("-pressed_at")
        ctx["main_playlist"] = main
        ctx["other_playlists"] = others
        return ctx


class PlaylistPageView(TemplateView):
    template_name = "public/playlist.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        playlist = get_object_or_404(
            Playlist, slug=self.kwargs["slug"], status=Playlist.Status.PUBLISHED
        )
        ctx["playlist"] = playlist
        ctx["items"] = playlist.items.select_related("media_item__provider")
        return ctx
