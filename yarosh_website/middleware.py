import uuid

from django.conf import settings
from django.core import signing

from .models import SiteVisitor


VISITOR_COOKIE_NAME = "yarosh_visitor"
VISITOR_COOKIE_AGE = 60 * 60 * 24 * 365
VISITOR_COOKIE_SALT = "yarosh_website.unique_visitor"


class UniqueSiteVisitorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        cookie_value = request.COOKIES.get(VISITOR_COOKIE_NAME)
        visitor_id, valid_cookie = self._visitor_id_from_cookie(cookie_value)
        if self._should_track(request):
            SiteVisitor.objects.get_or_create(pk=visitor_id)
            request.site_visitor_id = visitor_id
            response = self.get_response(request)
            if not valid_cookie:
                response.set_cookie(
                    VISITOR_COOKIE_NAME,
                    signing.dumps(str(visitor_id), salt=VISITOR_COOKIE_SALT),
                    max_age=VISITOR_COOKIE_AGE,
                    httponly=True,
                    secure=request.is_secure(),
                    samesite="Lax",
                )
            return response
        request.site_visitor_id = visitor_id if cookie_value and valid_cookie else None
        return self.get_response(request)

    @staticmethod
    def _should_track(request):
        static_url = f"/{settings.STATIC_URL.lstrip('/')}"
        media_url = f"/{settings.MEDIA_URL.lstrip('/')}"
        return (
            request.method == "GET"
            and not request.path_info.startswith(("/admin/", static_url, media_url))
            and request.path_info != "/stats/"
        )

    @staticmethod
    def _visitor_id_from_cookie(cookie_value):
        if cookie_value:
            try:
                signed_id = signing.loads(
                    cookie_value,
                    salt=VISITOR_COOKIE_SALT,
                    max_age=VISITOR_COOKIE_AGE,
                )
                return uuid.UUID(signed_id), True
            except (signing.BadSignature, ValueError, TypeError):
                pass
        return uuid.uuid4(), False
