from .models import PhotoSession, SiteVisitor


def site_stats(request):
    del request
    return {
        "visits_count": SiteVisitor.objects.count(),
        "photos_count": PhotoSession.objects.count(),
    }
