from django.test import TestCase
from django.contrib.auth import get_user_model
from providers.models import Provider
from content.models import MediaItem
from playlists.models import Playlist, PlaylistItem

User = get_user_model()


class PlaylistModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="staff", password="pass", is_staff=True)
        self.provider = Provider.objects.create(
            name="Test Provider",
            description="A test provider",
            url="https://example.com",
            logo="",
        )

    def test_single_main_playlist(self):
        p1 = Playlist.objects.create(title="P1", is_main=True, created_by=self.user)
        p2 = Playlist.objects.create(title="P2", is_main=True, created_by=self.user)
        p1.refresh_from_db()
        self.assertFalse(p1.is_main, "Old main playlist should be unset")
        self.assertTrue(p2.is_main)

    def test_slug_auto_generated(self):
        p = Playlist.objects.create(title="My Playlist", created_by=self.user)
        self.assertEqual(p.slug, "my-playlist")

    def test_playlist_item_effective_duration(self):
        media = MediaItem.objects.create(
            title="Test Image",
            media_type=MediaItem.MediaType.IMAGE,
            file="media/test.jpg",
            provider=self.provider,
            duration=10,
            uploaded_by=self.user,
        )
        playlist = Playlist.objects.create(title="P", created_by=self.user)
        item = PlaylistItem.objects.create(playlist=playlist, media_item=media, order=0)
        self.assertEqual(item.effective_duration, 10)

        item.duration_override = 20
        item.save()
        self.assertEqual(item.effective_duration, 20)


class AuthTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="staff", password="pass", is_staff=True)
        self.plain_user = User.objects.create_user(username="viewer", password="pass", is_staff=False)

    def test_manage_home_requires_staff(self):
        resp = self.client.get("/manage/")
        self.assertRedirects(resp, "/auth/login/?next=/manage/")

    def test_manage_home_accessible_to_staff(self):
        self.client.login(username="staff", password="pass")
        resp = self.client.get("/manage/")
        self.assertEqual(resp.status_code, 200)

    def test_manage_home_forbidden_to_non_staff(self):
        self.client.login(username="viewer", password="pass")
        resp = self.client.get("/manage/")
        self.assertEqual(resp.status_code, 403)

    def test_front_page_public(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
