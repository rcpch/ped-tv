from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse

from .mixins import StaffRequiredMixin
from .forms import ProviderForm, MediaItemForm, PlaylistForm
from providers.models import Provider
from content.models import MediaItem
from playlists.models import Playlist, PlaylistItem


# ---------------------------------------------------------------------------
# Management home
# ---------------------------------------------------------------------------

class ManageHomeView(StaffRequiredMixin, TemplateView):
    template_name = "manage/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        playlists = Playlist.objects.exclude(status=Playlist.Status.ARCHIVED)
        # Main playlist first, then oldest-to-newest
        ctx["playlists"] = sorted(
            playlists, key=lambda p: (0 if p.is_main else 1, p.created_at)
        )
        return ctx


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

class ProviderListView(StaffRequiredMixin, ListView):
    model = Provider
    template_name = "manage/providers/list.html"
    context_object_name = "providers"


class ProviderCreateView(StaffRequiredMixin, CreateView):
    model = Provider
    form_class = ProviderForm
    template_name = "manage/providers/form.html"
    success_url = reverse_lazy("manage:provider-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["action"] = "Add provider"
        return ctx


class ProviderUpdateView(StaffRequiredMixin, UpdateView):
    model = Provider
    form_class = ProviderForm
    template_name = "manage/providers/form.html"
    success_url = reverse_lazy("manage:provider-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["action"] = "Edit provider"
        return ctx


class ProviderDeleteView(StaffRequiredMixin, DeleteView):
    model = Provider
    template_name = "manage/providers/confirm_delete.html"
    success_url = reverse_lazy("manage:provider-list")


# ---------------------------------------------------------------------------
# Playlists
# ---------------------------------------------------------------------------

class PlaylistCreateView(StaffRequiredMixin, TemplateView):
    template_name = "manage/playlists/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = PlaylistForm()
        ctx["action"] = "Create playlist"
        return ctx

    def post(self, request):
        form = PlaylistForm(request.POST)
        if form.is_valid():
            playlist = Playlist.objects.create(
                title=form.cleaned_data["title"],
                created_by=request.user,
            )
            return redirect("manage:playlist-edit", pk=playlist.pk)
        return self.render_to_response(self.get_context_data(form=form))


class PlaylistEditView(StaffRequiredMixin, TemplateView):
    template_name = "manage/playlists/edit.html"

    def get_playlist(self):
        return get_object_or_404(Playlist, pk=self.kwargs["pk"])

    def get(self, request, **kwargs):
        playlist = self.get_playlist()
        if request.GET.get("status_fragment"):
            html = render_to_string(
                "manage/playlists/_status_tag.html",
                {"playlist": playlist},
                request=request,
            )
            return HttpResponse(html)
        return super().get(request, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        playlist = self.get_playlist()
        ctx["playlist"] = playlist
        items = list(playlist.items.select_related("media_item__provider"))
        ctx["items"] = items
        ctx["available_media"] = MediaItem.objects.select_related("provider")
        ctx["media_form"] = MediaItemForm()

        # Compute total playlist duration
        total = 0.0
        has_unknown = False
        for item in items:
            if item.media_item.is_image:
                total += item.effective_duration  # always known (defaults to 10)
            elif item.media_item.video_duration is not None:
                total += item.media_item.video_duration
            else:
                has_unknown = True
        ctx["total_duration"] = total
        ctx["total_duration_approx"] = has_unknown
        return ctx

    def post(self, request, pk):
        playlist = get_object_or_404(Playlist, pk=pk)
        action = request.POST.get("action")

        if action == "add_media":
            media_id = request.POST.get("media_id")
            media = get_object_or_404(MediaItem, pk=media_id)
            last_order = playlist.items.order_by("-order").values_list("order", flat=True).first() or 0
            PlaylistItem.objects.get_or_create(
                playlist=playlist,
                media_item=media,
                defaults={"order": last_order + 1},
            )

        elif action == "remove_media":
            item_id = request.POST.get("item_id")
            playlist.items.filter(pk=item_id).delete()

        elif action == "set_duration":
            item_id = request.POST.get("item_id")
            try:
                dur = int(request.POST.get("duration", 0))
                if dur > 0:
                    playlist.items.filter(
                        pk=item_id, media_item__media_type="image"
                    ).update(duration=dur)
            except (ValueError, TypeError):
                pass

        elif action == "reorder":
            order_ids = request.POST.getlist("order[]")
            for index, item_id in enumerate(order_ids):
                playlist.items.filter(pk=item_id).update(order=index)

        elif action == "set_main":
            playlist.is_main = True
            playlist.save()
            messages.success(request, f'"{playlist.title}" is now the main playlist.')

        elif action == "archive":
            playlist.status = Playlist.Status.ARCHIVED
            playlist.is_main = False
            playlist.save()
            messages.success(request, f'"{playlist.title}" has been archived.')
            return redirect("manage:home")

        elif action == "publish":
            from playlists.tasks import press_playlist
            playlist.status = Playlist.Status.PRESSING
            playlist.press_error = ""
            playlist.save()
            result = press_playlist.enqueue(playlist.pk)
            playlist.press_task_id = result.id
            playlist.save(update_fields=["press_task_id"])
            messages.success(request, "Press started — this may take a few minutes.")

        return redirect("manage:playlist-edit", pk=pk)


# ---------------------------------------------------------------------------
# Media upload
# ---------------------------------------------------------------------------

class MediaUploadView(StaffRequiredMixin, TemplateView):
    template_name = "manage/media/upload.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = MediaItemForm()
        return ctx

    def post(self, request):
        form = MediaItemForm(request.POST, request.FILES)
        if form.is_valid():
            media = form.save(commit=False)
            media.uploaded_by = request.user
            media.save()
            from content.tasks import generate_thumbnail
            generate_thumbnail.enqueue(media.pk)
            messages.success(request, f'"{media.title}" uploaded. Thumbnail is being generated.')
            return redirect("manage:media-upload")
        return self.render_to_response({"form": form})

