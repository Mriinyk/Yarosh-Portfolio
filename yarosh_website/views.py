from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic.edit import CreateView

from .contact_services import send_telegram_notification
from .forms import ContactForm, SiteAuthenticationForm, SiteUserCreationForm
from .models import HeroSlide, PhotoSession
from .photo_gallery import PhotoGalleryError, get_photo_session_images


def index(request):
    slides = HeroSlide.objects.filter(is_active=True)
    photo_sessions = PhotoSession.objects.filter(is_active=True)
    return render(
        request,
        "yarosh_website/index.html",
        {"slides": slides, "photo_sessions": photo_sessions},
    )


def photo_session_gallery(request, pk):
    del request
    photo_session = get_object_or_404(PhotoSession, pk=pk, is_active=True)
    try:
        images = get_photo_session_images(photo_session)
    except PhotoGalleryError as error:
        return JsonResponse({"error": str(error)}, status=502)
    return JsonResponse({"images": images})


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
