"""
MODELOS DE DATOS - Tienda de Hardware y Componentes PC

Diagrama de relaciones (integridad referencial):
    User 1---1 Perfil            (rol del usuario: CLIENTE / ADMINISTRADOR)
    User 1---1 Carro             (un único carro activo por usuario)
    Carro 1---N ItemCarro N---1 Producto
    Categoria 1---N Producto
    User 1---N Orden 1---N DetalleOrden N---1 Producto
"""
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


# ===========================================================================
# CATÁLOGO
# ===========================================================================
class Categoria(models.Model):
    """Categoría de productos (Procesadores, Tarjetas de Video, RAM, etc.)."""
    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    """Componente de hardware que se vende en la tienda."""
    nombre = models.CharField(max_length=150)
    marca = models.CharField(max_length=60)
    # Precio unitario en pesos chilenos (sin decimales).
    precio = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    # SKU: código único que identifica al producto en bodega.
    sku = models.CharField(max_length=40, unique=True)
    descripcion = models.TextField(blank=True)
    # Stock físico disponible. Solo se modifica al PAGAR o CANCELAR una orden.
    stock = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)
    # PROTECT: no se puede borrar una categoría que todavía tiene productos.
    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, related_name="productos"
    )
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.sku})"


# ===========================================================================
# USUARIOS Y ROLES
# ===========================================================================
class Perfil(models.Model):
    """
    Extiende al User de Django con el ROL. Este rol viaja dentro del token JWT
    como claim personalizado y define los permisos en la API.
    """
    # Propiedad CHOICES (requisito de la evaluación).
    class Rol(models.TextChoices):
        CLIENTE = "CLIENTE", "Cliente"
        ADMINISTRADOR = "ADMINISTRADOR", "Administrador de TI"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil"
    )
    rol = models.CharField(max_length=15, choices=Rol.choices, default=Rol.CLIENTE)

    def __str__(self):
        return f"{self.user.username} - {self.rol}"


# ===========================================================================
# CARRO DE COMPRAS PERSISTENTE
# ===========================================================================
class Carro(models.Model):
    """
    Carro de compras del usuario. Relación 1 a 1 con User: cada usuario tiene
    UN carro activo guardado en PostgreSQL. Como vive en la BD (y no en la
    sesión), los ítems se conservan tras el logout o al entrar desde otro
    dispositivo.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="carro"
    )
    actualizado = models.DateTimeField(auto_now=True)

    def total(self):
        return sum(i.subtotal() for i in self.items.select_related("producto"))

    def __str__(self):
        return f"Carro de {self.user.username}"


class ItemCarro(models.Model):
    """Línea del carro: un producto con su cantidad."""
    carro = models.ForeignKey(Carro, on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        # Un mismo producto NO puede repetirse en el carro: si se vuelve a
        # agregar, se suma la cantidad sobre la línea existente.
        constraints = [
            models.UniqueConstraint(fields=["carro", "producto"], name="producto_unico_por_carro")
        ]

    def subtotal(self):
        return self.producto.precio * self.cantidad


# ===========================================================================
# ÓRDENES (HISTÓRICO DE COMPRAS)
# ===========================================================================
class Orden(models.Model):
    """
    Orden de compra generada en el checkout.
    Ciclo de vida:  PENDIENTE -> PAGADO -> ENTREGADO
                    PENDIENTE -> CANCELADO   /   PAGADO -> CANCELADO
    """
    # Propiedad CHOICES (requisito de la evaluación).
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        PAGADO = "PAGADO", "Pagado"
        ENTREGADO = "ENTREGADO", "Entregado"
        CANCELADO = "CANCELADO", "Cancelado"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ordenes"
    )
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    total = models.PositiveIntegerField(default=0)
    # Bandera de control: True solo si el stock de esta orden YA fue descontado.
    # Evita descontar dos veces o reponer stock que nunca se descontó.
    stock_descontado = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return f"Orden #{self.pk} - {self.estado}"


class DetalleOrden(models.Model):
    """
    Línea de la orden. Guarda una COPIA del precio al momento del checkout
    (precio_unitario), por lo que cambios futuros en el catálogo no afectan
    ventas ya realizadas.
    """
    orden = models.ForeignKey(Orden, on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.PositiveIntegerField()  # precio congelado

    def subtotal(self):
        return self.precio_unitario * self.cantidad
