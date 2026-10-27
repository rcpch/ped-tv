import re

from django.core import mail
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
            uploaded_by=self.user,
        )
        playlist = Playlist.objects.create(title="P", created_by=self.user)
        item = PlaylistItem.objects.create(playlist=playlist, media_item=media, order=0)
        # Image display duration defaults to 10s when not explicitly set
        self.assertEqual(item.effective_duration, 10)

        item.duration = 20
        item.save()
        self.assertEqual(item.effective_duration, 20)


class PasswordResetFlowTests(TestCase):
    """Self-service password reset: request a link by email, then set a new password."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="staff",
            password="old-password-123",
            email="staff@example.com",
            is_staff=True,
        )

    def test_login_page_links_to_password_reset(self):
        resp = self.client.get("/auth/login/")
        self.assertContains(resp, 'href="/auth/password_reset/"')

    def test_reset_request_page_renders(self):
        resp = self.client.get("/auth/password_reset/")
        self.assertEqual(resp.status_code, 200)

    def test_full_reset_flow(self):
        # 1. Request a reset link
        resp = self.client.post("/auth/password_reset/", {"email": "staff@example.com"})
        self.assertRedirects(resp, "/auth/password_reset/done/")

        # 2. One email sent, to the right person
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(["staff@example.com"], email.to)
        self.assertIn("password", email.subject.lower())

        # 3. Open the link. Django 5.2 validates the token, stores it in the
        #    session, and redirects to a tokenless URL so the token doesn't
        #    linger in the browser's address bar.
        url = re.search(r"http://\S+", email.body).group()
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        set_password_url = resp["Location"]
        self.assertRegex(set_password_url, r"^/auth/reset/\w+/set-password/$")
        resp = self.client.get(set_password_url)
        self.assertContains(resp, "Choose a new password")

        # 4. Set a new password
        new_password = "new-secure-password-456"
        resp = self.client.post(set_password_url, {
            "new_password1": new_password,
            "new_password2": new_password,
        })
        self.assertRedirects(resp, "/auth/reset/done/")

        # 5. Old password rejected, new one works
        self.client.logout()
        self.assertFalse(self.client.login(username="staff", password="old-password-123"))
        self.assertTrue(self.client.login(username="staff", password=new_password))

    def test_unknown_email_sends_no_email_but_same_response(self):
        # Anti-enumeration: unknown addresses get the same redirect as real ones.
        resp = self.client.post("/auth/password_reset/", {"email": "nobody@example.com"})
        self.assertRedirects(resp, "/auth/password_reset/done/")
        self.assertEqual(len(mail.outbox), 0)

    def test_link_is_single_use(self):
        self.client.post("/auth/password_reset/", {"email": "staff@example.com"})
        url = re.search(r"http://\S+", mail.outbox[0].body).group()
        set_password_url = self.client.get(url)["Location"]
        new_password = "new-secure-password-456"
        self.client.post(set_password_url, {
            "new_password1": new_password,
            "new_password2": new_password,
        })

        # Opening the used link again shows the expired page — the token
        # no longer validates once the password has changed.
        resp = self.client.get(url)
        self.assertContains(resp, "expired")

        # And posting to it again does not change the password.
        resp = self.client.post(url, {
            "new_password1": "another-password-789",
            "new_password2": "another-password-789",
        })
        self.assertContains(resp, "expired")
        self.assertTrue(self.client.login(username="staff", password=new_password))
        self.assertFalse(self.client.login(username="staff", password="another-password-789"))

    def test_garbage_link_shows_expired_page(self):
        resp = self.client.get("/auth/reset/not-a-real-uid/not-a-real-token/")
        self.assertContains(resp, "expired")


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
