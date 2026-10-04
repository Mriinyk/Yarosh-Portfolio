from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic.edit import CreateView

from .contact_services import send_telegram_notification
from .forms import ContactForm, SiteAuthenticationForm, SiteUserCreationForm


def index(request):
    return render(request, 'yarosh_website/index.html')


def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            contact_request = form.save()
            if send_telegram_notification(contact_request):
                messages.success(request, "Дякуємо! Ваше повідомлення надіслано.")
            else:
                messages.error(
                    request,
                    "Повідомлення збережено, але сповіщення не вдалося надіслати.",
                )
            return redirect("contact")
    else:
        form = ContactForm()

    return render(request, "yarosh_website/contact.html", {"form": form})


class SiteLoginView(LoginView):
    template_name = "yarosh_website/auth/login.html"
    authentication_form = SiteAuthenticationForm
    redirect_authenticated_user = True


class SignUpView(CreateView):
    form_class = SiteUserCreationForm
    template_name = "yarosh_website/auth/signup.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["next"] = self.get_safe_next_url()
        return context

    def get_safe_next_url(self):
        next_url = self.request.POST.get("next") or self.request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            return next_url
        return None

    def get_success_url(self):
        return self.get_safe_next_url() or reverse("index")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


logout_view = LogoutView.as_view()
