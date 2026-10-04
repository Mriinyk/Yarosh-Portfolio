from django.urls import path
from . import views


urlpatterns = [
    path("", views.index, name="index"),
    path("photos/", views.photo_sessions, name="photos"),
    path("photos/add/", views.photo_session_create, name="photo_session_create"),
    path(
        "photos/<int:pk>/edit/",
        views.photo_session_update,
        name="photo_session_update",
    ),
    path(
        "photos/<int:pk>/delete/",
        views.photo_session_delete,
        name="photo_session_delete",
    ),
    path("stats/", views.site_stats, name="site_stats"),
    path("contact/", views.contact, name="contact"),
    path(
        "photo-sessions/<int:pk>/like/",
        views.photo_session_like,
        name="photo_session_like",
    ),
    path(
        "photo-sessions/<int:pk>/comment/",
        views.photo_session_comment,
        name="photo_session_comment",
    ),
    path(
        "photo-sessions/<int:pk>/share/",
        views.photo_session_share,
        name="photo_session_share",
    ),
    path(
        "photo-sessions/<int:pk>/gallery/",
        views.photo_session_gallery,
        name="photo_session_gallery",
    ),
    path(
        "accounts/login/",
        views.SiteLoginView.as_view(),
        name="login",
    ),
    path("accounts/signup/", views.SignUpView.as_view(), name="signup"),
    path(
        "accounts/logout/",
        views.logout_view,
        name="logout",
    ),
]
