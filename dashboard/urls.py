from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from . import views
from . import views_gsg

urlpatterns = [
    path("gsg/", views_gsg.index, name="gsg_index"),
    path("gsg/reports/", views_gsg.reports, name="gsg_reports"),
    path("gsg/billing/", views_gsg.billing, name="gsg_billing"),
    path('oidc/', include('mozilla_django_oidc.urls')),
    #path("install/<uuid:pk>/", views.install, name="install")
    path('', views.index, name='index'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
