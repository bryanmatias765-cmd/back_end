"""
Comando para poblar la BD con datos de ejemplo (categorías y productos tipo
tienda de componentes PC) y dos usuarios de prueba.
Uso:  python manage.py cargar_datos
Los precios (CLP) y stocks son referenciales, solo para demostración.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from api.models import Categoria, Producto

CATALOGO = {
    "Procesadores": [
        ("AMD Ryzen 5 5600", "AMD", 129990, "AMD-R5-5600", "6 núcleos / 12 hilos, socket AM4", 15),
        ("AMD Ryzen 7 5700X", "AMD", 189990, "AMD-R7-5700X", "8 núcleos / 16 hilos, socket AM4", 10),
        ("AMD Ryzen 5 7600X", "AMD", 219990, "AMD-R5-7600X", "6 núcleos, socket AM5", 8),
        ("Intel Core i5-12400F", "Intel", 139990, "INT-I5-12400F", "6 núcleos, socket LGA1700, sin video integrado", 12),
        ("Intel Core i7-13700K", "Intel", 359990, "INT-I7-13700K", "16 núcleos híbridos, socket LGA1700", 6),
    ],
    "Tarjetas de Video": [
        ("GeForce RTX 4060 8GB", "ASUS", 329990, "ASU-RTX4060-8G", "8GB GDDR6, DLSS 3", 9),
        ("GeForce RTX 4070 Super 12GB", "MSI", 689990, "MSI-RTX4070S-12G", "12GB GDDR6X", 5),
        ("Radeon RX 7600 8GB", "Gigabyte", 279990, "GIG-RX7600-8G", "8GB GDDR6", 7),
        ("Radeon RX 7800 XT 16GB", "Sapphire", 549990, "SAP-RX7800XT-16G", "16GB GDDR6", 4),
    ],
    "Placas Madre": [
        ("ASUS PRIME B550M-K", "ASUS", 84990, "ASU-B550M-K", "Micro-ATX, socket AM4, DDR4", 14),
        ("MSI PRO B760M-P DDR4", "MSI", 99990, "MSI-B760M-P", "Micro-ATX, socket LGA1700, DDR4", 11),
        ("Gigabyte B650 AORUS Elite AX", "Gigabyte", 189990, "GIG-B650-AE", "ATX, socket AM5, DDR5, WiFi", 6),
    ],
    "Memorias RAM": [
        ("Kingston Fury Beast 16GB (2x8) DDR4 3200", "Kingston", 42990, "KIN-FB-16-D4", "Kit dual channel DDR4", 30),
        ("Corsair Vengeance 32GB (2x16) DDR5 6000", "Corsair", 109990, "COR-VG-32-D5", "Kit dual channel DDR5", 12),
        ("TeamGroup T-Force 16GB DDR4 3600", "TeamGroup", 39990, "TEA-TF-16-D4", "Módulo único DDR4", 20),
    ],
    "Almacenamiento": [
        ("SSD NVMe Kingston NV2 1TB", "Kingston", 54990, "KIN-NV2-1TB", "M.2 PCIe 4.0", 25),
        ("SSD NVMe WD Black SN770 1TB", "Western Digital", 79990, "WD-SN770-1TB", "M.2 PCIe 4.0, hasta 5150 MB/s", 18),
        ("Disco Duro Seagate Barracuda 2TB", "Seagate", 59990, "SEA-BC-2TB", "HDD 3.5\" 7200 RPM", 16),
    ],
    "Fuentes de Poder": [
        ("Fuente Corsair CX650 650W 80+ Bronze", "Corsair", 64990, "COR-CX650", "No modular", 13),
        ("Fuente Cooler Master MWE 750W Gold", "Cooler Master", 89990, "CM-MWE750G", "80+ Gold, semi modular", 9),
    ],
    "Gabinetes": [
        ("Gabinete NZXT H510 Flow", "NZXT", 89990, "NZX-H510F", "Mid tower, panel lateral de vidrio", 8),
        ("Gabinete Cooler Master MasterBox Q300L", "Cooler Master", 44990, "CM-Q300L", "Micro-ATX", 10),
    ],
    "Monitores": [
        ("Monitor Gamer LG 24\" 144Hz IPS", "LG", 129990, "LG-24GN60R", "Full HD, 1ms, FreeSync", 7),
        ("Monitor Samsung Odyssey G5 27\" 165Hz", "Samsung", 209990, "SAM-G5-27", "QHD, curvo, VA", 5),
    ],
}


class Command(BaseCommand):
    help = "Carga categorías, productos y usuarios de ejemplo."

    def handle(self, *args, **options):
        # get_or_create: el comando se puede ejecutar varias veces sin duplicar datos.
        for nombre_cat, productos in CATALOGO.items():
            categoria, _ = Categoria.objects.get_or_create(nombre=nombre_cat)
            for nombre, marca, precio, sku, desc, stock in productos:
                Producto.objects.get_or_create(
                    sku=sku,
                    defaults=dict(nombre=nombre, marca=marca, precio=precio,
                                  descripcion=desc, stock=stock, categoria=categoria),
                )

        User = get_user_model()
        # Usuarios de prueba (cambia estas contraseñas fuera del ambiente de desarrollo).
        if not User.objects.filter(username="admin_ti").exists():
            User.objects.create_superuser("admin_ti", "admin@tienda.cl", "Admin12345!")
        if not User.objects.filter(username="cliente1").exists():
            User.objects.create_user("cliente1", "cliente1@correo.cl", "Cliente12345!")

        self.stdout.write(self.style.SUCCESS(
            f"Listo: {Categoria.objects.count()} categorías, {Producto.objects.count()} productos.\n"
            "Usuarios: admin_ti / Admin12345!  (ADMINISTRADOR)   |   cliente1 / Cliente12345!  (CLIENTE)"
        ))
