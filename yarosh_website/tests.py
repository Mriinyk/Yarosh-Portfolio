from unittest.mock import Mock, patch

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .contact_services import send_telegram_notification
from .models import (
    Biography,
    ContactRequest,
    HeroSlide,
    PhotoSession,
    PhotoSessionComment,
    PhotoSessionLike,
    PhotoSessionShare,
    PhotoSessionType,
    SiteVisitor,
)


class HomePageTemplateTests(TestCase):
    def test_hero_slide_normalizes_google_drive_image_links(self):
        drive_url = "https://drive.google.com/file/d/example-id/view?usp=sharing"
        slide = HeroSlide(image_url=drive_url)

        self.assertEqual(
            slide.direct_image_url,
            "https://lh3.googleusercontent.com/d/example-id",
        )

        slide.save()
        slide.refresh_from_db()
        self.assertEqual(
            slide.image_url,
            "https://lh3.googleusercontent.com/d/example-id",
        )

    def test_homepage_uses_google_drive_direct_image_url(self):
        drive_url = "https://drive.google.com/open?id=google-drive-id"
        slide = HeroSlide.objects.create(
            image_url="https://images.example.com/placeholder.jpg",
        )
        HeroSlide.objects.filter(pk=slide.pk).update(image_url=drive_url)

        response = self.client.get(reverse("index"))

        self.assertContains(
            response,
            f'src="https://lh3.googleusercontent.com/d/google-drive-id"',
        )
        self.assertNotContains(response, drive_url)

    def test_homepage_shows_empty_slider_when_no_active_slides_exist(self):
        response = self.client.get(reverse("index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Поки немає слайдів")
        self.assertContains(response, "yarosh_website/js/hero-slider.js")
        self.assertNotContains(response, "data-hero-slider")

    def test_homepage_renders_active_slides_in_configured_order(self):
        second = HeroSlide.objects.create(
            image_url="https://images.example.com/second.jpg",
            order=2,
        )
        inactive = HeroSlide.objects.create(
            image_url="https://images.example.com/hidden.jpg",
            order=1,
            is_active=False,
        )
        first = HeroSlide.objects.create(
            image_url="https://images.example.com/first.jpg",
            order=1,
        )

        response = self.client.get(reverse("index"))
        rendered = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Yarosh Oleksandra")
        self.assertContains(response, "data-interval=\"5000\"")
        self.assertContains(response, "yarosh_website/js/hero-slider.js")
        self.assertContains(response, 'loading="eager"')
        self.assertContains(response, 'class="hero-slide is-active"')
        self.assertContains(response, 'class="hero-slide"')
        self.assertNotContains(response, inactive.image_url)
        self.assertLess(rendered.index(first.image_url), rendered.index(second.image_url))

    def test_hero_slides_are_registered_with_order_and_active_admin_controls(self):
        hero_admin = admin.site._registry[HeroSlide]

        self.assertIn("image_url", hero_admin.list_display)
        self.assertIn("order", hero_admin.list_editable)
        self.assertIn("is_active", hero_admin.list_editable)
        self.assertEqual(hero_admin.ordering, ("order", "pk"))

    def test_homepage_renders_shared_layout_and_navigation(self):
        response = self.client.get(reverse("index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Yarosh Portfolio")
        self.assertContains(response, "Головна")
        self.assertContains(response, "Фотосесії")
        self.assertContains(response, "Увійти")
        self.assertContains(response, "Зв'язатися")
        self.assertContains(response, 'id="siteThemeToggle"')
        self.assertContains(response, 'id="siteThemeToggleMobile"')
        self.assertContains(response, "Увімкнути темну тему")
        self.assertContains(response, "yarosh_website/images/logo.png")
        self.assertContains(response, "yarosh_website/css/style.css")
        self.assertContains(response, "yarosh_website/js/theme.js")
        self.assertContains(response, f'href="{reverse("contact")}"')
        rendered = response.content.decode()
        self.assertLess(
            rendered.index('id="siteThemeToggleMobile"'),
            rendered.index('id="siteNavbar"'),
        )
        self.assertLess(
            rendered.index('class="site-header"'),
            rendered.index('class="hero-slider"'),
        )

    def test_login_navigation_opens_login_page(self):
        response = self.client.get(reverse("index"))

        self.assertContains(response, f'href="{reverse("login")}?next=/')


    def test_homepage_renders_active_photo_sessions_in_order(self):
        later = PhotoSession.objects.create(
            title="Пізніша фотосесія",
            cover_url="https://images.example.com/later.jpg",
            drive_folder_url="https://drive.google.com/drive/folders/later-id",
            order=2,
        )
        PhotoSession.objects.create(
            title="Прихована фотосесія",
            cover_url="https://images.example.com/hidden.jpg",
            drive_folder_url="https://drive.google.com/drive/folders/hidden-id",
            order=0,
            is_active=False,
        )
        earlier = PhotoSession.objects.create(
            title="Раніша фотосесія",
            cover_url="https://drive.google.com/file/d/cover-id/view",
            drive_folder_url="https://drive.google.com/drive/folders/earlier-id",
            order=1,
        )

        response = self.client.get(reverse("index"))
        rendered = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "НОВІ ФОТОСЕСІЇ")
        self.assertContains(response, 'id="photosessions"')
        self.assertContains(response, "photo-sessions.js")
        self.assertNotContains(response, "data-carousel-direction")
        self.assertContains(response, "Відкрити альбом: Раніша фотосесія")
        self.assertContains(response, 'src="https://lh3.googleusercontent.com/d/cover-id"')
        self.assertNotContains(response, "Прихована фотосесія")
        self.assertLess(rendered.index(earlier.title), rendered.index(later.title))

    def test_homepage_shows_empty_photo_sessions_message(self):
        response = self.client.get(reverse("index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Незабаром тут з'являться нові фотосесії.")

    def test_homepage_renders_biography_section_with_seeded_text(self):
        response = self.client.get(reverse("index"))
        rendered = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="biography"')
        self.assertContains(response, "Олександра Ярош")
        self.assertContains(response, "yarosh_website/images/Biographical.jpg")
        self.assertLess(
            rendered.index('id="photosessions"'),
            rendered.index('id="biography"'),
        )

    def test_homepage_biography_uses_uploaded_photo_when_present(self):
        biography = Biography.objects.first()
        biography.photo = "biography/custom.jpg"
        biography.save(update_fields=["photo"])

        response = self.client.get(reverse("index"))

        self.assertContains(response, "biography/custom.jpg")
        self.assertNotContains(response, "Biographical.jpg")

    def test_photo_session_cover_normalization_and_folder_id(self):
        photo_session = PhotoSession(
            title="Портрет",
            cover_url="https://drive.google.com/open?id=cover-file-id",
            drive_folder_url="https://drive.google.com/drive/folders/folder-id",
        )

        self.assertEqual(
            photo_session.direct_cover_url,
            "https://lh3.googleusercontent.com/d/cover-file-id",
        )
        self.assertEqual(photo_session.get_drive_folder_id(), "folder-id")

    def test_photo_session_gallery_endpoint_returns_cover_and_folder_images(self):
        from django.core.cache import cache

        cache.clear()
        photo_session = PhotoSession.objects.create(
            title="Портрет",
            cover_url="https://drive.google.com/file/d/cover-file-id/view",
            drive_folder_url="https://drive.google.com/drive/folders/folder-id",
        )
        response_from_drive = Mock()
        response_from_drive.text = (
            '<tr data-selectable="true" data-id="cover-file-id">'
            '<td data-tooltip="cover.jpg"></td></tr>'
            '<tr data-selectable="true" data-id="gallery-file-id">'
            '<td data-tooltip="gallery.jpeg"></td></tr>'
            '<tr data-selectable="true" data-id="not-an-image">'
            '<td data-tooltip="document.pdf"></td></tr>'
        )
        response_from_drive.raise_for_status.return_value = None

        with patch(
            "yarosh_website.photo_gallery.requests.get",
            return_value=response_from_drive,
        ) as drive_get:
            response = self.client.get(
                reverse("photo_session_gallery", args=[photo_session.pk])
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["images"],
            [
                "https://lh3.googleusercontent.com/d/cover-file-id",
                "https://lh3.googleusercontent.com/d/gallery-file-id",
            ],
        )
        drive_get.assert_called_once()

    def test_gallery_parser_handles_drive_markup_variants_and_more_image_types(self):
        from .photo_gallery import _extract_image_file_ids

        folder_html = (
            "<table><tr data-selectable data-id='root-file-id'>"
            "<td data-id='nested-preview-id' "
            "data-tooltip='IMG_5697.jpg&quot; Image'></td>"
            "<td aria-label='IMG_5697.jpg Image Shared'></td></tr></table>"
            "<div data-id='standalone-id' "
            "aria-label='preview.avif'></div>"
            "<div data-id='document-id' "
            "data-tooltip='document.pdf'></div>"
        )

        self.assertEqual(
            _extract_image_file_ids(folder_html),
            ["root-file-id", "standalone-id"],
        )

    def test_photo_session_gallery_endpoint_reports_invalid_folder_link(self):
        photo_session = PhotoSession.objects.create(
            title="Портрет",
            cover_url="https://images.example.com/cover.jpg",
            drive_folder_url="https://drive.google.com/drive/my-drive",
        )

        response = self.client.get(
            reverse("photo_session_gallery", args=[photo_session.pk])
        )

        self.assertEqual(response.status_code, 502)
        self.assertIn("error", response.json())

    def test_photo_session_gallery_endpoint_reports_empty_or_unavailable_folder(self):
        from django.core.cache import cache

        cache.clear()
        photo_session = PhotoSession.objects.create(
            title="Портрет",
            cover_url="https://images.example.com/cover.jpg",
            drive_folder_url="https://drive.google.com/drive/folders/empty-id",
        )
        response_from_drive = Mock()
        response_from_drive.text = "<html>Sign in to Google Drive</html>"
        response_from_drive.raise_for_status.return_value = None

        with patch(
            "yarosh_website.photo_gallery.requests.get",
            return_value=response_from_drive,
        ):
            response = self.client.get(
                reverse("photo_session_gallery", args=[photo_session.pk])
            )

        self.assertEqual(response.status_code, 502)
        self.assertIn("error", response.json())

    def test_photo_session_gallery_endpoint_rejects_cached_empty_folder(self):
        from django.core.cache import cache

        photo_session = PhotoSession.objects.create(
            title="Портрет",
            cover_url="https://images.example.com/cover.jpg",
            drive_folder_url="https://drive.google.com/drive/folders/cached-empty-id",
        )
        cache.set("photo-session-gallery:cached-empty-id", [], 60)

        with patch("yarosh_website.photo_gallery.requests.get") as drive_get:
            response = self.client.get(
                reverse("photo_session_gallery", args=[photo_session.pk])
            )

        self.assertEqual(response.status_code, 502)
        self.assertIn("error", response.json())
        drive_get.assert_not_called()

    def test_inactive_photo_session_gallery_is_not_public(self):
        photo_session = PhotoSession.objects.create(
            title="Архів",
            cover_url="https://images.example.com/cover.jpg",
            drive_folder_url="https://drive.google.com/drive/folders/archive-id",
            is_active=False,
        )

        response = self.client.get(
            reverse("photo_session_gallery", args=[photo_session.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_photo_sessions_are_registered_without_manual_order_or_activation(self):
        photo_admin = admin.site._registry[PhotoSession]

        self.assertIn("title", photo_admin.list_display)
        self.assertNotIn("order", photo_admin.list_display)
        self.assertNotIn("is_active", photo_admin.list_display)
        self.assertEqual(photo_admin.ordering, ("-created_at", "-pk"))
        self.assertEqual(
            photo_admin.fields,
            ("title", "photo_type", "cover_url", "drive_folder_url"),
        )


class AuthenticationFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="existing-user",
            password="Valid-Test-Password-123!",
        )

    def test_login_page_renders_form_and_signup_link(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "yarosh_website/auth/login.html")
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')
        self.assertContains(response, reverse("signup"))
        self.assertContains(response, "yarosh_website/images/logo.png")
        self.assertContains(response, "yarosh_website/js/auth.js")
        self.assertNotContains(response, "autofocus")

    def test_signup_page_renders_form_and_login_link(self):
        response = self.client.get(reverse("signup"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "yarosh_website/auth/signup.html")
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password1"')
        self.assertContains(response, 'name="password2"')
        self.assertContains(response, reverse("login"))
        self.assertContains(response, "yarosh_website/images/logo.png")
        self.assertContains(response, "yarosh_website/js/auth.js")
        self.assertNotContains(response, "autofocus")

    def test_login_success_redirects_to_home_and_shows_account_controls(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "existing-user",
                "password": "Valid-Test-Password-123!",
            },
        )

        self.assertRedirects(response, reverse("index"))
        homepage = self.client.get(reverse("index"))
        self.assertContains(homepage, "existing-user")
        self.assertContains(homepage, reverse("logout"))
        self.assertNotContains(homepage, "Увійти")
        self.assertContains(homepage, "Вийти з акаунта")

    def test_login_rejects_incorrect_password(self):
        response = self.client.post(
            reverse("login"),
            {"username": "existing-user", "password": "incorrect"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].non_field_errors())

    def test_signup_creates_user_logs_them_in_and_rejects_external_next(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "new-user",
                "password1": "Strong-Test-Password-937!",
                "password2": "Strong-Test-Password-937!",
                "next": "https://example.com/",
            },
        )

        self.assertRedirects(response, reverse("index"))
        self.assertTrue(
            get_user_model().objects.filter(username="new-user").exists()
        )
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_logout_clears_session(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("logout"))

        self.assertRedirects(response, reverse("index"))
        homepage = self.client.get(reverse("index"))
        self.assertContains(homepage, "Увійти")
        self.assertNotContains(homepage, "existing-user")

    def test_custom_user_model_is_registered_with_django_user_admin(self):
        user_model = get_user_model()

        self.assertEqual(user_model._meta.label, "yarosh_website.User")
        self.assertEqual(user_model._meta.db_table, "auth_user")
        self.assertIsInstance(admin.site._registry[user_model], UserAdmin)


class ContactFlowTests(TestCase):
    def test_contact_page_renders_form_logo_and_script(self):
        response = self.client.get(reverse("contact"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "yarosh_website/contact.html")
        self.assertContains(response, "yarosh_website/images/logo.png")
        self.assertContains(response, 'name="contact_method"')
        self.assertContains(response, 'name="social_username"')
        self.assertContains(response, 'name="message"')
        self.assertContains(response, "yarosh_website/js/contact.js")
        self.assertContains(response, 'class="contact-messages"')
        self.assertNotContains(response, 'class="contact-message ')

    @patch("yarosh_website.views.send_telegram_notification", return_value=True)
    def test_valid_submission_is_saved_and_reports_success(self, mock_notify):
        response = self.client.post(
            reverse("contact"),
            {
                "contact_method": "telegram",
                "social_username": "@viewer",
                "message": "Please contact me",
            },
            follow=True,
        )

        self.assertEqual(ContactRequest.objects.count(), 1)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Дякуємо! Ваше повідомлення надіслано.")
        self.assertContains(response, 'class="contact-messages"')
        self.assertContains(response, 'class="contact-message contact-message-success"')
        mock_notify.assert_called_once()

    @patch("yarosh_website.views.send_telegram_notification", return_value=False)
    def test_delivery_failure_keeps_request_and_reports_error(self, mock_notify):
        response = self.client.post(
            reverse("contact"),
            {
                "contact_method": "instagram",
                "social_username": "@viewer",
                "message": "Please contact me",
            },
            follow=True,
        )

        self.assertEqual(ContactRequest.objects.count(), 1)
        self.assertContains(
            response,
            "Повідомлення збережено, але сповіщення не вдалося надіслати.",
        )
        mock_notify.assert_called_once()

    def test_invalid_submission_is_not_saved(self):
        response = self.client.post(
            reverse("contact"),
            {
                "contact_method": "unsupported",
                "social_username": "@viewer",
                "message": "Please contact me",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactRequest.objects.count(), 0)
        self.assertTrue(response.context["form"].errors)

    @patch("yarosh_website.contact_services.requests.post")
    def test_unconfigured_telegram_is_reported_without_network_request(self, mock_post):
        contact_request = ContactRequest.objects.create(
            contact_method="telegram",
            social_username="@viewer",
            message="Please contact me",
        )

        with (
            self.settings(TELEGRAM_BOT_TOKEN="", TELEGRAM_CHAT_ID=""),
            self.assertLogs("yarosh_website.contact_services", level="ERROR"),
        ):
            sent = send_telegram_notification(contact_request)

        self.assertFalse(sent)
        mock_post.assert_not_called()

    @patch("yarosh_website.contact_services.requests.post")
    def test_telegram_notification_escapes_content_and_saves_message_id(self, mock_post):
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": True,
            "result": {"message_id": 456},
        }
        mock_post.return_value = mock_response
        contact_request = ContactRequest.objects.create(
            contact_method="telegram",
            social_username="@viewer",
            message="<script>alert('x')</script> & hello",
        )

        with self.settings(TELEGRAM_BOT_TOKEN="test-token", TELEGRAM_CHAT_ID="-100123"):
            sent = send_telegram_notification(contact_request)

        self.assertTrue(sent)
        contact_request.refresh_from_db()
        self.assertEqual(contact_request.telegram_message_id, 456)
        request_data = mock_post.call_args.kwargs["json"]
        self.assertIn("&lt;script&gt;", request_data["text"])
        self.assertIn("&amp; hello", request_data["text"])
        mock_post.assert_called_once_with(
            "https://api.telegram.org/bottest-token/sendMessage",
            json=request_data,
            timeout=5,
        )

    @patch("yarosh_website.contact_services.requests.post")
    def test_invalid_telegram_response_is_reported(self, mock_post):
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = []
        mock_post.return_value = mock_response
        contact_request = ContactRequest.objects.create(
            contact_method="telegram",
            social_username="@viewer",
            message="Please contact me",
        )

        with (
            self.settings(TELEGRAM_BOT_TOKEN="test-token", TELEGRAM_CHAT_ID="-100123"),
            self.assertLogs("yarosh_website.contact_services", level="ERROR"),
        ):
            sent = send_telegram_notification(contact_request)

        self.assertFalse(sent)
        contact_request.refresh_from_db()
        self.assertIsNone(contact_request.telegram_message_id)

    @patch("yarosh_website.contact_services.requests.post")
    def test_deleting_request_deletes_telegram_message(self, mock_post):
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "result": True}
        mock_post.return_value = mock_response
        contact_request = ContactRequest.objects.create(
            contact_method="instagram",
            social_username="@viewer",
            message="Please contact me",
            telegram_message_id=789,
        )

        with self.settings(TELEGRAM_BOT_TOKEN="test-token", TELEGRAM_CHAT_ID="-100123"):
            contact_request.delete()

        self.assertFalse(ContactRequest.objects.filter(pk=contact_request.pk).exists())
        mock_post.assert_called_once_with(
            "https://api.telegram.org/bottest-token/deleteMessage",
            json={"chat_id": "-100123", "message_id": 789},
            timeout=5,
        )

    def test_contact_requests_are_registered_for_admin_management(self):
        contact_admin = admin.site._registry[ContactRequest]
        request = Mock()
        contact_request = ContactRequest.objects.create(
            contact_method="telegram",
            social_username="@viewer",
            message="Please contact me",
        )

        contact_admin.delete_queryset(request, [contact_request])

        self.assertFalse(ContactRequest.objects.filter(pk=contact_request.pk).exists())

    def test_admin_list_shows_clickable_truncated_message_before_created_date(self):
        admin_user = get_user_model().objects.create_superuser(
            username="contact-admin",
            password="Strong-Admin-Password-123!",
        )
        self.client.force_login(admin_user)
        message = "A contact message that is long enough to be shortened in the admin list."
        contact_request = ContactRequest.objects.create(
            contact_method="telegram",
            social_username="@viewer",
            message=message,
        )

        response = self.client.get(reverse("admin:yarosh_website_contactrequest_changelist"))
        change_url = reverse(
            "admin:yarosh_website_contactrequest_change",
            args=(contact_request.pk,),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'href="{change_url}"')
        self.assertContains(response, "A contact message that is long enough")
        detail_response = self.client.get(change_url)
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, message)
        contact_admin = admin.site._registry[ContactRequest]
        self.assertEqual(
            contact_admin.list_display.index("message_preview"),
            contact_admin.list_display.index("social_username") + 1,
        )
        self.assertEqual(
            contact_admin.list_display.index("created_at"),
            contact_admin.list_display.index("message_preview") + 1,
        )


class PhotoSessionPageTests(TestCase):
    def setUp(self):
        self.photo_type = PhotoSessionType.objects.get(name="Портрети")
        self.photo_session = PhotoSession.objects.create(
            title="Літній портрет",
            photo_type=self.photo_type,
            cover_url="https://images.example.com/portrait.jpg",
            drive_folder_url="https://drive.google.com/drive/folders/portrait",
        )

    def test_navbar_photo_link_opens_the_paginated_photo_page(self):
        home = self.client.get(reverse("index"))
        photos = self.client.get(reverse("photos"))

        self.assertContains(home, f'href="{reverse("photos")}">Фотосесії</a>')
        self.assertEqual(photos.status_code, 200)
        self.assertIn("csrftoken", photos.cookies)
        self.assertContains(photos, "Літній портрет")
        self.assertContains(photos, "Портрети")
        self.assertContains(photos, 'data-gallery-url=')

    def test_photo_page_filters_by_type_and_search_term(self):
        other_type = PhotoSessionType.objects.get(name="Заходи")
        PhotoSession.objects.create(
            title="Корпоратив",
            photo_type=other_type,
            cover_url="https://images.example.com/event.jpg",
            drive_folder_url="https://drive.google.com/drive/folders/event",
        )

        by_type = self.client.get(
            reverse("photos"),
            {"type": self.photo_type.pk},
        )
        by_search = self.client.get(reverse("photos"), {"q": "літній"})

        self.assertEqual(
            [session.title for session in by_type.context["photo_sessions"]],
            ["Літній портрет"],
        )
        self.assertEqual(
            [session.title for session in by_search.context["photo_sessions"]],
            ["Літній портрет"],
        )

    def test_uncategorized_sessions_can_be_filtered_for_legacy_content(self):
        uncategorized = PhotoSession.objects.create(
            title="Стара фотосесія",
            cover_url="https://images.example.com/legacy.jpg",
            drive_folder_url="https://drive.google.com/drive/folders/legacy",
        )

        response = self.client.get(reverse("photos"), {"type": "none"})

        self.assertEqual(
            [session.pk for session in response.context["photo_sessions"]],
            [uncategorized.pk],
        )
        self.assertContains(response, "Без категорії")

    def test_photo_page_shows_nine_sessions_per_page_and_preserves_filters(self):
        for index in range(9):
            PhotoSession.objects.create(
                title=f"Портрет {index}",
                photo_type=self.photo_type,
                cover_url=f"https://images.example.com/portrait-{index}.jpg",
                drive_folder_url=f"https://drive.google.com/drive/folders/p-{index}",
            )

        response = self.client.get(
            reverse("photos"),
            {"q": "Портрет", "type": self.photo_type.pk},
        )

        self.assertEqual(len(response.context["photo_sessions"]), 9)
        self.assertTrue(response.context["page_obj"].has_next())
        self.assertContains(response, "page=2")
        self.assertContains(response, f"type={self.photo_type.pk}")

    def test_photo_sessions_are_ordered_newest_first(self):
        older = PhotoSession.objects.create(
            title="Стара фотосесія",
            photo_type=self.photo_type,
            cover_url="https://images.example.com/older.jpg",
            drive_folder_url="https://drive.google.com/drive/folders/older",
        )
        newer = PhotoSession.objects.create(
            title="Нова фотосесія",
            photo_type=self.photo_type,
            cover_url="https://images.example.com/newer.jpg",
            drive_folder_url="https://drive.google.com/drive/folders/newer",
        )

        response = self.client.get(reverse("photos"))

        ordered_ids = [
            session.pk for session in response.context["photo_sessions"]
        ]
        self.assertLess(ordered_ids.index(newer.pk), ordered_ids.index(older.pk))
        self.assertEqual(PhotoSession._meta.ordering, ["-created_at", "-pk"])

    def test_photo_form_has_category_choices_but_no_order_or_active_controls(self):
        self.client.force_login(
            get_user_model().objects.create_superuser(
                username="form-admin",
                password="Safe-password-123",
                email="form-admin@example.com",
            )
        )
        response = self.client.get(reverse("photo_session_create"))

        self.assertContains(response, "Без категорії")
        self.assertContains(response, "Додати нову категорію")
        self.assertContains(response, 'data-new-category-field hidden')
        self.assertNotContains(response, "Порядок показу")
        self.assertNotContains(response, "Активна")
        self.assertNotContains(response, "Новий тип")
        self.assertNotIn("order", response.context["form"].fields)
        self.assertNotIn("is_active", response.context["form"].fields)

    def test_superuser_can_create_session_with_a_new_category_or_no_category(self):
        administrator = get_user_model().objects.create_superuser(
            username="photo-admin",
            password="Safe-password-123",
            email="photo-admin@example.com",
        )
        self.client.force_login(administrator)

        response = self.client.post(
            reverse("photo_session_create"),
            {
                "title": "Нова тематична зйомка",
                "photo_type": "__new__",
                "new_category": "Казкові образи",
                "cover_url": "https://images.example.com/fairy.jpg",
                "drive_folder_url": "https://drive.google.com/drive/folders/fairy",
            },
        )

        new_type = PhotoSessionType.objects.get(name="Казкові образи")
        created = PhotoSession.objects.get(title="Нова тематична зйомка")
        self.assertRedirects(response, reverse("photos"))
        self.assertEqual(created.photo_type, new_type)
        self.assertTrue(created.is_active)
        self.assertContains(self.client.get(reverse("photos")), "Казкові образи")

        uncategorized_response = self.client.post(
            reverse("photo_session_create"),
            {
                "title": "Фотосесія без категорії",
                "photo_type": "",
                "new_category": "",
                "cover_url": "https://images.example.com/uncategorized.jpg",
                "drive_folder_url": "https://drive.google.com/drive/folders/uncategorized",
            },
        )

        uncategorized = PhotoSession.objects.get(title="Фотосесія без категорії")
        self.assertRedirects(uncategorized_response, reverse("photos"))
        self.assertIsNone(uncategorized.photo_type)
        self.assertTrue(uncategorized.is_active)

    def test_non_superuser_cannot_open_photo_session_editor(self):
        viewer = get_user_model().objects.create_user(
            username="photo-viewer",
            password="Safe-password-123",
        )
        self.client.force_login(viewer)

        response = self.client.get(
            reverse("photo_session_update", args=[self.photo_session.pk])
        )

        self.assertEqual(response.status_code, 403)

    def test_superuser_can_update_and_delete_a_photo_session(self):
        administrator = get_user_model().objects.create_superuser(
            username="photo-editor",
            password="Safe-password-123",
            email="photo-editor@example.com",
        )
        self.client.force_login(administrator)
        update_response = self.client.post(
            reverse("photo_session_update", args=[self.photo_session.pk]),
            {
                "title": "Оновлений портрет",
                "photo_type": str(self.photo_type.pk),
                "new_category": "",
                "cover_url": "https://images.example.com/updated.jpg",
                "drive_folder_url": "https://drive.google.com/drive/folders/updated",
            },
        )

        self.assertRedirects(update_response, reverse("photos"))
        self.photo_session.refresh_from_db()
        self.assertEqual(self.photo_session.title, "Оновлений портрет")

        delete_response = self.client.post(
            reverse("photo_session_delete", args=[self.photo_session.pk])
        )
        self.assertRedirects(delete_response, reverse("photos"))
        self.assertFalse(PhotoSession.objects.filter(pk=self.photo_session.pk).exists())

    def test_authenticated_like_can_be_toggled_and_is_admin_registered(self):
        viewer = get_user_model().objects.create_user(
            username="photo-liker",
            password="Safe-password-123",
        )
        self.client.force_login(viewer)
        url = reverse("photo_session_like", args=[self.photo_session.pk])

        first = self.client.post(url)
        second = self.client.post(url)

        self.assertEqual(first.json(), {"liked": True, "likes_count": 1})
        self.assertEqual(second.json(), {"liked": False, "likes_count": 0})
        self.assertEqual(PhotoSessionLike.objects.count(), 0)
        self.assertIn(PhotoSessionLike, admin.site._registry)

    def test_authenticated_comment_is_created_and_registered_in_admin(self):
        viewer = get_user_model().objects.create_user(
            username="photo-commenter",
            password="Safe-password-123",
        )
        self.client.force_login(viewer)

        response = self.client.post(
            reverse("photo_session_comment", args=[self.photo_session.pk]),
            {"text": "Чудове фото!"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["comment_count"], 1)
        self.assertTrue(
            PhotoSessionComment.objects.filter(
                photo_session=self.photo_session,
                user=viewer,
                text="Чудове фото!",
            ).exists()
        )
        self.assertIn(PhotoSessionComment, admin.site._registry)

    def test_share_action_is_recorded_for_anonymous_visitors(self):
        self.client.get(reverse("photos"))

        response = self.client.post(
            reverse("photo_session_share", args=[self.photo_session.pk])
        )

        share = PhotoSessionShare.objects.get()
        self.assertEqual(response.json(), {"shares_count": 1})
        self.assertIsNotNone(share.visitor)
        self.assertIn(PhotoSessionShare, admin.site._registry)


class UniqueVisitorCounterTests(TestCase):
    def test_unique_device_is_counted_once_across_pages_and_stats_refresh(self):
        first_page = self.client.get(reverse("index"))
        self.assertEqual(SiteVisitor.objects.count(), 1)
        self.assertIn("yarosh_visitor", first_page.cookies)

        self.client.get(reverse("photos"))
        stats = self.client.get(reverse("site_stats"))

        self.assertEqual(SiteVisitor.objects.count(), 1)
        self.assertEqual(stats.json()["visits"], 1)
        self.assertEqual(stats.json()["photo_sessions"], 0)

        another_device = self.client_class()
        another_device.get(reverse("contact"))
        self.assertEqual(SiteVisitor.objects.count(), 2)

    def test_footer_is_shared_and_excludes_the_video_counter(self):
        response = self.client.get(reverse("contact"))

        self.assertContains(response, "Унікальні відвідувачі")
        self.assertContains(response, "Фотосесії")
        self.assertNotContains(response, "Кількість відеоробіт")
