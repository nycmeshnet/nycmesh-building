from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("reports", views.reports, name="reports"),
    path("billing", views.billing, name="billing")
    #path("install/<uuid:pk>/", views.install, name="install")
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)