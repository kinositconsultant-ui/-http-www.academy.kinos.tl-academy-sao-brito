"""Root URL configuration. All routes under /api/ (ingress requirement)."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    # Redirect bare root to /api/ (in case anyone hits it)
    path("", RedirectView.as_view(url="/api/dashboard/", permanent=False)),
    path("api/admin/", admin.site.urls),
    path("api/", include("accounts.urls")),
    path("api/", include("erp.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
