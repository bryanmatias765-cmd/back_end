"""URLs raíz del proyecto."""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from api import views as api_views

urlpatterns = [
    path("", api_views.inicio, name="inicio"),
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    # Documentación OpenAPI / Swagger
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
