"""
SERIALIZADORES: convierten modelos <-> JSON y validan los datos de entrada.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Categoria, DetalleOrden, ItemCarro, Orden, Producto

User = get_user_model()


# ---------------------------------------------------------------------------
# AUTENTICACIÓN
# ---------------------------------------------------------------------------
class RolTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Login JWT con PAYLOAD PERSONALIZADO: agrega el claim "rol" (y el username)
    dentro del token access/refresh. Así el frontend sabe qué rol tiene el
    usuario sin consultar la BD.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["rol"] = user.perfil.rol
        token["username"] = user.username
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # También devolvemos el rol en el cuerpo de la respuesta (comodidad).
        data["rol"] = self.user.perfil.rol
        return data


class RegistroSerializer(serializers.ModelSerializer):
    """Registro público: SIEMPRE crea usuarios CLIENTE (el rol no se puede elegir)."""
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def validate_password(self, value):
        validate_password(value)  # aplica los validadores de contraseña de Django
        return value

    def create(self, validated_data):
        # create_user hashea la contraseña; la señal crea Perfil(CLIENTE) y Carro.
        return User.objects.create_user(**validated_data)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


# ---------------------------------------------------------------------------
# CATÁLOGO
# ---------------------------------------------------------------------------
class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = "__all__"


class ProductoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)

    class Meta:
        model = Producto
        fields = [
            "id", "nombre", "marca", "precio", "sku", "descripcion",
            "stock", "activo", "categoria", "categoria_nombre",
        ]


# ---------------------------------------------------------------------------
# CARRO
# ---------------------------------------------------------------------------
class ItemCarroSerializer(serializers.ModelSerializer):
    producto_id = serializers.IntegerField(source="producto.id", read_only=True)
    nombre = serializers.CharField(source="producto.nombre", read_only=True)
    precio = serializers.IntegerField(source="producto.precio", read_only=True)
    subtotal = serializers.IntegerField(read_only=True)

    class Meta:
        model = ItemCarro
        fields = ["producto_id", "nombre", "precio", "cantidad", "subtotal"]


class CarroSerializer(serializers.Serializer):
    items = ItemCarroSerializer(many=True)
    total = serializers.IntegerField()


class AgregarItemSerializer(serializers.Serializer):
    """Entrada para agregar un producto al carro."""
    producto = serializers.PrimaryKeyRelatedField(queryset=Producto.objects.filter(activo=True))
    cantidad = serializers.IntegerField(min_value=1, default=1)


class CantidadSerializer(serializers.Serializer):
    """Entrada para modificar la cantidad de una línea del carro."""
    cantidad = serializers.IntegerField(min_value=1)


# ---------------------------------------------------------------------------
# ÓRDENES
# ---------------------------------------------------------------------------
class DetalleOrdenSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    subtotal = serializers.IntegerField(read_only=True)

    class Meta:
        model = DetalleOrden
        fields = ["producto", "producto_nombre", "cantidad", "precio_unitario", "subtotal"]


class OrdenSerializer(serializers.ModelSerializer):
    detalles = DetalleOrdenSerializer(many=True, read_only=True)
    usuario = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Orden
        fields = ["id", "usuario", "estado", "total", "creado", "actualizado", "detalles"]


class CambiarEstadoSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(choices=Orden.Estado.choices)
