from unittest.mock import Mock, patch

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .contact_services import send_telegram_notification
from .models import ContactRequest


class HomePageTemplateTests(TestCase):
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

    def test_login_navigation_opens_login_page(self):
        response = self.client.get(reverse("index"))

        self.assertContains(response, f'href="{reverse("login")}?next=/')


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
