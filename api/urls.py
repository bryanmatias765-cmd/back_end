"""Rutas de la API (todas cuelgan de /api/)."""
from django.urls import include, path
from rest_framework import routers
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

router = routers.DefaultRouter()
router.register(r"productos", views.ProductoViewSet, basename="producto")
router.register(r"categorias", views.CategoriaViewSet, basename="categoria")
router.register(r"mis-ordenes", views.MisOrdenesViewSet, basename="mis-ordenes")
router.register(r"ordenes", views.OrdenesAdminViewSet, basename="ordenes")

urlpatterns = [
    # Autenticación JWT
    path("auth/registro/", views.RegistroView.as_view(), name="registro"),
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="refresh"),
    path("auth/logout/", views.LogoutView.as_view(), name="logout"),
    # Carro persistente
    path("carro/", views.CarroView.as_view(), name="carro"),
    path("carro/items/<int:producto_id>/", views.ItemCarroView.as_view(), name="carro-item"),
    # Órdenes (las rutas explícitas van ANTES del router para que no choquen con /ordenes/<pk>/)
    path("ordenes/checkout/", views.CheckoutView.as_view(), name="checkout"),
    path("ordenes/<int:pk>/pagar/", views.PagarOrdenView.as_view(), name="pagar"),
    path("ordenes/<int:pk>/estado/", views.CambiarEstadoView.as_view(), name="estado"),
    # Catálogo y listados (router)
    path("", include(router.urls)),
]
