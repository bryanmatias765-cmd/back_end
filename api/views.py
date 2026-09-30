"""
VISTAS DE LA API
Matriz de permisos:
  PÚBLICO       : GET productos, GET categorías, registro, login
  CLIENTE (JWT) : carro, checkout, pagar, mis-ordenes
  ADMINISTRADOR : POST/PUT/PATCH/DELETE productos y categorías, cambiar estado de órdenes
"""
from django.db.models import ProtectedError
from django.shortcuts import render
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from . import services
from .filters import OrdenFilter, ProductoFilter
from .models import Categoria, ItemCarro, Orden, Producto
from .permissions import EsAdministrador, LecturaPublicaEscrituraAdmin, es_admin
from .serializers import (
    AgregarItemSerializer, CambiarEstadoSerializer, CantidadSerializer,
    CarroSerializer, CategoriaSerializer, LogoutSerializer, OrdenSerializer,
    ProductoSerializer, RegistroSerializer, RolTokenObtainPairSerializer,
)


# ===========================================================================
# PÁGINA HTML BASE (con footer del alumno)
# ===========================================================================
def inicio(request):
    """Vista HTML simple: catálogo estilo tienda, con filtro por categoría."""
    productos = Producto.objects.filter(activo=True).select_related("categoria")
    categoria_id = request.GET.get("categoria")
    if categoria_id:
        productos = productos.filter(categoria_id=categoria_id)
    return render(request, "api/inicio.html", {
        "categorias": Categoria.objects.all(),
        "productos": productos[:48],
        "categoria_actual": categoria_id,
    })


# ===========================================================================
# AUTENTICACIÓN
# ===========================================================================
class LoginView(TokenObtainPairView):
    """Login: devuelve access + refresh (con el claim "rol" dentro del token)."""
    serializer_class = RolTokenObtainPairSerializer


class RegistroView(generics.CreateAPIView):
    """Registro público de clientes."""
    serializer_class = RegistroSerializer
    permission_classes = [AllowAny]


class LogoutView(APIView):
    """
    Logout: mete el refresh token en la lista negra. El carro NO se borra:
    vive en PostgreSQL y estará intacto en el próximo login.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(request=LogoutSerializer, responses={205: None})
    def post(self, request):
        ser = LogoutSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            RefreshToken(ser.validated_data["refresh"]).blacklist()
        except TokenError:
            return Response({"detalle": "Token inválido o expirado."}, status=400)
        return Response(status=status.HTTP_205_RESET_CONTENT)


# ===========================================================================
# CATÁLOGO (lectura pública / escritura solo administrador)
# ===========================================================================
class _ProtegeBorrado:
    """Mixin: si un registro está referenciado por órdenes, responde 409 en vez de error 500."""

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detalle": "No se puede eliminar: tiene registros asociados. "
                            "Para productos, desactívalo con activo=false."},
                status=status.HTTP_409_CONFLICT,
            )


class CategoriaViewSet(_ProtegeBorrado, viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [LecturaPublicaEscrituraAdmin]
    search_fields = ["nombre"]


class ProductoViewSet(_ProtegeBorrado, viewsets.ModelViewSet):
    serializer_class = ProductoSerializer
    permission_classes = [LecturaPublicaEscrituraAdmin]
    filterset_class = ProductoFilter          # filtros (django-filter)
    search_fields = ["nombre", "marca", "sku", "descripcion"]
    ordering_fields = ["precio", "nombre", "stock"]

    def get_queryset(self):
        qs = Producto.objects.select_related("categoria")
        # El público y los clientes solo ven productos activos; el admin ve todo.
        return qs if es_admin(self.request.user) else qs.filter(activo=True)


# ===========================================================================
# CARRO PERSISTENTE (solo usuarios autenticados)
# ===========================================================================
class CarroView(APIView):
    """
    GET    /api/carro/  -> ver mi carro
    POST   /api/carro/  -> agregar producto (si ya existe, suma la cantidad)
    DELETE /api/carro/  -> vaciar el carro
    """
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _respuesta(carro, codigo=200):
        return Response(CarroSerializer(carro).data, status=codigo)

    @extend_schema(responses=CarroSerializer)
    def get(self, request):
        return self._respuesta(_CarroWrapper(request.user.carro))

    @extend_schema(request=AgregarItemSerializer, responses=CarroSerializer)
    def post(self, request):
        ser = AgregarItemSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        producto, cantidad = ser.validated_data["producto"], ser.validated_data["cantidad"]
        carro = request.user.carro
        # get_or_create + suma: evita productos duplicados dentro del mismo carro.
        item, creado = ItemCarro.objects.get_or_create(
            carro=carro, producto=producto, defaults={"cantidad": cantidad}
        )
        if not creado:
            item.cantidad += cantidad
            item.save(update_fields=["cantidad"])
        return self._respuesta(_CarroWrapper(carro), status.HTTP_201_CREATED)

    @extend_schema(responses={204: None})
    def delete(self, request):
        request.user.carro.items.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class _CarroWrapper:
    """Adapta el Carro al formato {items, total} que espera CarroSerializer."""
    def __init__(self, carro):
        self.items = list(carro.items.select_related("producto"))
        self.total = sum(i.subtotal() for i in self.items)


class ItemCarroView(APIView):
    """
    PATCH  /api/carro/items/{producto_id}/ -> modificar cantidad
    DELETE /api/carro/items/{producto_id}/ -> eliminar el ítem
    """
    permission_classes = [IsAuthenticated]

    def _item(self, request, producto_id):
        return generics.get_object_or_404(
            ItemCarro, carro=request.user.carro, producto_id=producto_id
        )

    @extend_schema(request=CantidadSerializer, responses=CarroSerializer)
    def patch(self, request, producto_id):
        item = self._item(request, producto_id)
        ser = CantidadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        item.cantidad = ser.validated_data["cantidad"]
        item.save(update_fields=["cantidad"])
        return Response(CarroSerializer(_CarroWrapper(request.user.carro)).data)

    @extend_schema(responses=CarroSerializer)
    def delete(self, request, producto_id):
        self._item(request, producto_id).delete()
        return Response(CarroSerializer(_CarroWrapper(request.user.carro)).data)


# ===========================================================================
# ÓRDENES
# ===========================================================================
def _ejecutar(funcion, *args):
    """Ejecuta un servicio y traduce los errores de negocio a respuestas HTTP."""
    try:
        return Response(OrdenSerializer(funcion(*args)).data), None
    except services.StockInsuficiente as e:
        return None, Response({"detalle": str(e)}, status=status.HTTP_409_CONFLICT)
    except services.ErrorDeNegocio as e:
        return None, Response({"detalle": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CheckoutView(APIView):
    """POST /api/ordenes/checkout/ -> genera la Orden PENDIENTE con precios congelados."""
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={201: OrdenSerializer})
    def post(self, request):
        ok, error = _ejecutar(services.crear_orden_desde_carro, request.user)
        if error:
            return error
        ok.status_code = status.HTTP_201_CREATED
        return ok


class PagarOrdenView(APIView):
    """
    POST /api/ordenes/{id}/pagar/ -> el cliente paga SU orden (pago simulado).
    Aquí se valida el stock y se descuenta (estado PAGADO).
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses=OrdenSerializer)
    def post(self, request, pk):
        # Solo puede pagar órdenes propias (404 si no es suya).
        orden = generics.get_object_or_404(Orden, pk=pk, user=request.user)
        ok, error = _ejecutar(services.cambiar_estado_orden, orden.pk, Orden.Estado.PAGADO)
        return error or ok


class CambiarEstadoView(APIView):
    """PATCH /api/ordenes/{id}/estado/ -> solo Administrador (ENTREGADO, CANCELADO, etc.)."""
    permission_classes = [EsAdministrador]

    @extend_schema(request=CambiarEstadoSerializer, responses=OrdenSerializer)
    def patch(self, request, pk):
        generics.get_object_or_404(Orden, pk=pk)
        ser = CambiarEstadoSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ok, error = _ejecutar(services.cambiar_estado_orden, pk, ser.validated_data["estado"])
        return error or ok


class MisOrdenesViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/mis-ordenes/ -> historial de compras del cliente autenticado."""
    serializer_class = OrdenSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["estado"]
    search_fields = []

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Orden.objects.none()
        return Orden.objects.filter(user=self.request.user).prefetch_related("detalles__producto")


class OrdenesAdminViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/ordenes/ -> todas las órdenes (solo Administrador), filtrables por estado/usuario."""
    queryset = Orden.objects.all().prefetch_related("detalles__producto")
    serializer_class = OrdenSerializer
    permission_classes = [EsAdministrador]
    filterset_class = OrdenFilter
