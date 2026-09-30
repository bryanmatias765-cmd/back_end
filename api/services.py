"""
SERVICIOS DE NEGOCIO: checkout, control de stock y cambio de estados.

Toda la lógica crítica vive aquí (y no en las vistas) para poder explicarla
y probarla por separado. Las funciones usan transaction.atomic(): si algo
falla a la mitad, PostgreSQL revierte TODOS los cambios (todo o nada).
"""
from django.db import transaction

from .models import DetalleOrden, Orden, Producto


class ErrorDeNegocio(Exception):
    """Error controlado que la vista convierte en una respuesta 400/409."""


class StockInsuficiente(ErrorDeNegocio):
    """Se intentó pagar una orden y algún producto no tiene stock suficiente."""


# Máquina de estados: qué transiciones están permitidas desde cada estado.
TRANSICIONES = {
    Orden.Estado.PENDIENTE: {Orden.Estado.PAGADO, Orden.Estado.CANCELADO},
    Orden.Estado.PAGADO: {Orden.Estado.ENTREGADO, Orden.Estado.CANCELADO},
    Orden.Estado.ENTREGADO: set(),   # estado final
    Orden.Estado.CANCELADO: set(),   # estado final
}


@transaction.atomic
def crear_orden_desde_carro(user):
    """
    CHECKOUT: convierte el carro del usuario en una Orden PENDIENTE.
      1. Copia cada ítem a DetalleOrden CONGELANDO el precio actual.
      2. Calcula el total.
      3. Vacía el carro.
    OJO: aquí NO se toca el stock (solo se descuenta al pasar a PAGADO).
    """
    carro = user.carro
    items = list(carro.items.select_related("producto"))
    if not items:
        raise ErrorDeNegocio("El carro está vacío.")

    inactivos = [i.producto.nombre for i in items if not i.producto.activo]
    if inactivos:
        raise ErrorDeNegocio(f"Productos ya no disponibles: {', '.join(inactivos)}")

    orden = Orden.objects.create(user=user, estado=Orden.Estado.PENDIENTE)
    total = 0
    for item in items:
        DetalleOrden.objects.create(
            orden=orden,
            producto=item.producto,
            cantidad=item.cantidad,
            precio_unitario=item.producto.precio,  # precio congelado
        )
        total += item.producto.precio * item.cantidad
    orden.total = total
    orden.save(update_fields=["total"])

    carro.items.all().delete()  # el carro queda vacío y listo para una nueva compra
    return orden


@transaction.atomic
def cambiar_estado_orden(orden_id, nuevo_estado):
    """
    Cambia el estado de una orden aplicando las reglas de inventario:
      * -> PAGADO   : verifica stock de TODOS los productos; si alguno no
                      alcanza, rechaza la transacción completa. Si alcanza,
                      descuenta el stock.
      * -> CANCELADO: si el stock ya había sido descontado, lo repone.
    """
    # select_for_update() bloquea la fila en PostgreSQL hasta terminar la
    # transacción: evita que dos pagos simultáneos vendan el mismo stock.
    orden = Orden.objects.select_for_update().get(pk=orden_id)

    if nuevo_estado not in TRANSICIONES[orden.estado]:
        raise ErrorDeNegocio(
            f"Transición no permitida: {orden.estado} -> {nuevo_estado}."
        )

    detalles = list(orden.detalles.all())
    # Se bloquean los productos ordenados por id (evita bloqueos cruzados/deadlocks).
    productos = {
        p.pk: p
        for p in Producto.objects.select_for_update()
        .filter(pk__in=[d.producto_id for d in detalles])
        .order_by("pk")
    }

    if nuevo_estado == Orden.Estado.PAGADO:
        # 1) Validar stock de todos los productos ANTES de descontar nada.
        faltantes = [
            f"{productos[d.producto_id].nombre} (pedido {d.cantidad}, disponible {productos[d.producto_id].stock})"
            for d in detalles
            if productos[d.producto_id].stock < d.cantidad
        ]
        if faltantes:
            raise StockInsuficiente("Stock insuficiente: " + "; ".join(faltantes))
        # 2) Descontar.
        for d in detalles:
            p = productos[d.producto_id]
            p.stock -= d.cantidad
            p.save(update_fields=["stock"])
        orden.stock_descontado = True

    elif nuevo_estado == Orden.Estado.CANCELADO and orden.stock_descontado:
        # Reposición automática al catálogo.
        for d in detalles:
            p = productos[d.producto_id]
            p.stock += d.cantidad
            p.save(update_fields=["stock"])
        orden.stock_descontado = False

    orden.estado = nuevo_estado
    orden.save(update_fields=["estado", "stock_descontado", "actualizado"])
    return orden
