from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from . import views_gsg

urlpatterns = [
    path("gsg/", views-gsg.index, name="index"),
    path("gsg/reports", views-gsg.reports, name="reports"),
    path("gsg/billing", views-gsg.billing, name="billing"),
    path('oidc/', include('mozilla_django_oidc.urls')),
    #path("install/<uuid:pk>/", views.install, name="install")
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
