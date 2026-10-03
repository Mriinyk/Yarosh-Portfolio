from django.urls import path
from . import views


urlpatterns = [
    path("", views.index, name="index"),
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
