"""
FILTROS con django-filter. Se aplican en /api/productos/ y en los listados de órdenes.
Ejemplos:
  /api/productos/?categoria=2&precio_min=50000&precio_max=200000
  /api/productos/?marca=amd&en_stock=true&ordering=precio
  /api/productos/?search=ryzen
"""
import django_filters as filters

from .models import Orden, Producto


class ProductoFilter(filters.FilterSet):
    # Rango de precios
    precio_min = filters.NumberFilter(field_name="precio", lookup_expr="gte")
    precio_max = filters.NumberFilter(field_name="precio", lookup_expr="lte")
    # Búsqueda parcial (sin distinguir mayúsculas)
    marca = filters.CharFilter(field_name="marca", lookup_expr="icontains")
    nombre = filters.CharFilter(field_name="nombre", lookup_expr="icontains")
    # Filtra por nombre de categoría (además del id con ?categoria=)
    categoria_nombre = filters.CharFilter(field_name="categoria__nombre", lookup_expr="icontains")
    # ?en_stock=true -> solo productos con stock > 0
    en_stock = filters.BooleanFilter(method="filtrar_en_stock")

    class Meta:
        model = Producto
        fields = ["categoria", "sku", "activo"]

    def filtrar_en_stock(self, queryset, name, value):
        if value is True:
            return queryset.filter(stock__gt=0)
        if value is False:
            return queryset.filter(stock=0)
        return queryset


class OrdenFilter(filters.FilterSet):
    class Meta:
        model = Orden
        fields = ["estado", "user"]
