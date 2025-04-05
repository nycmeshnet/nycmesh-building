from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from . import views_gsg

urlpatterns = [
    path("gsg/", views_gsg.index, name="index"),
    path("gsg/reports", views_gsg.reports, name="reports"),
    path("gsg/billing", views_gsg.billing, name="billing"),
    path('oidc/', include('mozilla_django_oidc.urls')),
    #path("install/<uuid:pk>/", views.install, name="install")
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
