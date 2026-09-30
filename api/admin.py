from django.contrib import admin

from .models import Carro, Categoria, DetalleOrden, ItemCarro, Orden, Perfil, Producto

admin.site.register(Categoria)
admin.site.register(Perfil)
admin.site.register(Carro)
admin.site.register(ItemCarro)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "marca", "sku", "precio", "stock", "categoria", "activo")
    list_filter = ("categoria", "marca", "activo")
    search_fields = ("nombre", "sku", "marca")


class DetalleInline(admin.TabularInline):
    model = DetalleOrden
    extra = 0


@admin.register(Orden)
class OrdenAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "estado", "total", "stock_descontado", "creado")
    list_filter = ("estado",)
    # El estado se cambia por la API (que aplica las reglas de stock), no a mano aquí.
    readonly_fields = ("estado", "stock_descontado", "total")
    inlines = [DetalleInline]
