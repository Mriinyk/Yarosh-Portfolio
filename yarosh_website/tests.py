from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model


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
