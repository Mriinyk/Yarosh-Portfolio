from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.views.generic.edit import CreateView

from .contact_services import send_telegram_notification
from .forms import (
    ContactForm,
    PhotoSessionForm,
    SiteAuthenticationForm,
    SiteUserCreationForm,
)
from .models import (
    Biography,
    HeroSlide,
    PhotoSession,
    PhotoSessionComment,
    PhotoSessionLike,
    PhotoSessionShare,
    PhotoSessionType,
    SiteVisitor,
)
from .photo_gallery import PhotoGalleryError, get_photo_session_images


def index(request):
    slides = HeroSlide.objects.filter(is_active=True)
    photo_sessions = PhotoSession.objects.filter(is_active=True)
    biography = Biography.objects.first()
    return render(
        request,
        "yarosh_website/index.html",
        {
            "slides": slides,
            "photo_sessions": photo_sessions,
            "biography": biography,
        },
    )


@ensure_csrf_cookie
def photo_sessions(request):
    search_query = request.GET.get("q", "").strip()
    selected_type = request.GET.get("type", "").strip()
    sessions = PhotoSession.objects.filter(is_active=True).select_related(
        "photo_type"
    ).prefetch_related(
        Prefetch(
            "comments",
            queryset=PhotoSessionComment.objects.select_related("user").order_by(
                "-created_at"
            ),
        )
    ).annotate(
        likes_count=Count("likes", distinct=True),
        comments_count=Count("comments", distinct=True),
        shares_count=Count("shares", distinct=True),
    )
    if search_query:
        normalized_query = search_query.casefold()
        sessions = sessions.filter(
            Q(search_title__contains=normalized_query)
            | Q(photo_type__search_name__contains=normalized_query)
        )
    if selected_type == "none":
        sessions = sessions.filter(photo_type__isnull=True)
    elif selected_type.isdigit():
        sessions = sessions.filter(photo_type_id=int(selected_type))
    elif selected_type:
        selected_type = ""

    paginator = Paginator(sessions.order_by("-created_at", "-pk"), 9)
    page_obj = paginator.get_page(request.GET.get("page"))
    liked_session_ids = set()
    if request.user.is_authenticated:
        liked_session_ids = set(
            PhotoSessionLike.objects.filter(
                user=request.user,
                photo_session__in=page_obj.object_list,
            ).values_list("photo_session_id", flat=True)
        )

    return render(
        request,
        "yarosh_website/photos.html",
        {
            "page_obj": page_obj,
            "photo_sessions": page_obj.object_list,
            "photo_types": PhotoSessionType.objects.all(),
            "search_query": search_query,
            "selected_type": selected_type,
            "has_uncategorized": PhotoSession.objects.filter(
                is_active=True,
                photo_type__isnull=True,
            ).exists(),
            "liked_session_ids": liked_session_ids,
        },
    )


def photo_session_gallery(request, pk):
    del request
    photo_session = get_object_or_404(PhotoSession, pk=pk, is_active=True)
    try:
        images = get_photo_session_images(photo_session)
    except PhotoGalleryError as error:
        return JsonResponse({"error": str(error)}, status=502)
    return JsonResponse({"images": images})


def site_stats(request):
    del request
    return JsonResponse(
        {
            "visits": SiteVisitor.objects.count(),
            "photo_sessions": PhotoSession.objects.count(),
        }
    )


@require_POST
def photo_session_share(request, pk):
    photo_session = get_object_or_404(PhotoSession, pk=pk, is_active=True)
    visitor = None
    visitor_id = getattr(request, "site_visitor_id", None)
    if visitor_id:
        visitor = SiteVisitor.objects.filter(pk=visitor_id).first()
    PhotoSessionShare.objects.create(
        photo_session=photo_session,
        user=request.user if request.user.is_authenticated else None,
        visitor=visitor,
    )
    return JsonResponse({"shares_count": photo_session.shares.count()})


@require_POST
def photo_session_like(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Увійдіть, щоб поставити вподобання."}, status=401)
    photo_session = get_object_or_404(PhotoSession, pk=pk, is_active=True)
    like, created = PhotoSessionLike.objects.get_or_create(
        photo_session=photo_session,
        user=request.user,
    )
    if not created:
        like.delete()
    return JsonResponse(
        {
            "liked": created,
            "likes_count": photo_session.likes.count(),
        }
    )


@require_POST
def photo_session_comment(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Увійдіть, щоб залишити коментар."}, status=401)
    photo_session = get_object_or_404(PhotoSession, pk=pk, is_active=True)
    text = request.POST.get("text", "").strip()
    if not text or len(text) > 2000:
        return JsonResponse(
            {"error": "Коментар має містити від 1 до 2000 символів."},
            status=400,
        )
    comment = PhotoSessionComment.objects.create(
        photo_session=photo_session,
        user=request.user,
        text=text,
    )
    return JsonResponse(
        {
            "status": "success",
            "username": comment.user.username,
            "text": comment.text,
            "created_at": comment.created_at.strftime("%d.%m.%Y %H:%M"),
            "comment_count": photo_session.comments.count(),
        }
    )


def photo_session_create(request):
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login')}?next={request.path}")
    if not request.user.is_superuser:
        raise PermissionDenied
    form = PhotoSessionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("photos")
    return render(
        request,
        "yarosh_website/photo_session_form.html",
        {"form": form, "page_title": "Додати фотосесію"},
    )


def photo_session_update(request, pk):
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login')}?next={request.path}")
    if not request.user.is_superuser:
        raise PermissionDenied
    photo_session = get_object_or_404(PhotoSession, pk=pk)
    form = PhotoSessionForm(request.POST or None, instance=photo_session)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("photos")
    return render(
        request,
        "yarosh_website/photo_session_form.html",
        {"form": form, "page_title": "Оновити фотосесію"},
    )


def photo_session_delete(request, pk):
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login')}?next={request.path}")
    if not request.user.is_superuser:
        raise PermissionDenied
    photo_session = get_object_or_404(PhotoSession, pk=pk)
    if request.method == "POST":
        photo_session.delete()
        return redirect("photos")
    return render(
        request,
        "yarosh_website/photo_session_confirm_delete.html",
        {"photo_session": photo_session},
    )


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
