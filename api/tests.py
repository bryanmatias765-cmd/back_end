"""
PRUEBAS AUTOMÁTICAS del flujo principal: JWT con rol, permisos, carro persistente,
checkout con precio congelado, descuento de stock al PAGAR y reposición al CANCELAR.
Ejecutar con:  python manage.py test
"""
import jwt  # PyJWT (dependencia de simplejwt)
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Categoria, Orden, Producto

User = get_user_model()


class FlujoTiendaTests(APITestCase):
    def setUp(self):
        self.cat = Categoria.objects.create(nombre="Procesadores")
        self.p1 = Producto.objects.create(nombre="CPU A", marca="AMD", precio=100000, sku="A1", stock=5, categoria=self.cat)
        self.p2 = Producto.objects.create(nombre="CPU B", marca="Intel", precio=200000, sku="B1", stock=1, categoria=self.cat)
        self.cliente = User.objects.create_user("cli", password="Cliente12345!")
        self.admin = User.objects.create_superuser("adm", password="Admin12345!")

    def login(self, username, password):
        r = self.client.post("/api/auth/login/", {"username": username, "password": password})
        self.assertEqual(r.status_code, 200)
        return r.data

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_jwt_incluye_claim_de_rol(self):
        data = self.login("cli", "Cliente12345!")
        claims = jwt.decode(data["access"], options={"verify_signature": False})
        self.assertEqual(claims["rol"], "CLIENTE")
        self.assertIn("refresh", data)
        self.assertEqual(jwt.decode(self.login("adm", "Admin12345!")["access"], options={"verify_signature": False})["rol"], "ADMINISTRADOR")

    def test_permisos_catalogo(self):
        self.assertEqual(self.client.get("/api/productos/").status_code, 200)   # público
        body = {"nombre": "X", "marca": "M", "precio": 1000, "sku": "X1", "stock": 1, "categoria": self.cat.id}
        self.assertEqual(self.client.post("/api/productos/", body).status_code, 401)  # anónimo
        self.auth(self.login("cli", "Cliente12345!")["access"])
        self.assertEqual(self.client.post("/api/productos/", body).status_code, 403)  # cliente
        self.auth(self.login("adm", "Admin12345!")["access"])
        self.assertEqual(self.client.post("/api/productos/", body).status_code, 201)  # admin

    def test_filtros(self):
        r = self.client.get("/api/productos/?precio_min=150000")
        self.assertEqual([p["sku"] for p in r.data["results"]], ["B1"])
        r = self.client.get("/api/productos/?marca=amd")
        self.assertEqual(r.data["count"], 1)
        r = self.client.get("/api/productos/?search=intel")
        self.assertEqual(r.data["count"], 1)

    def test_carro_persiste_tras_logout_y_no_duplica(self):
        tokens = self.login("cli", "Cliente12345!")
        self.auth(tokens["access"])
        self.client.post("/api/carro/", {"producto": self.p1.id, "cantidad": 2})
        self.client.post("/api/carro/", {"producto": self.p1.id, "cantidad": 1})  # suma, no duplica
        self.assertEqual(self.client.post("/api/auth/logout/", {"refresh": tokens["refresh"]}).status_code, 205)
        self.client.credentials()
        self.assertEqual(self.client.get("/api/carro/").status_code, 401)  # sin sesión
        self.auth(self.login("cli", "Cliente12345!")["access"])            # nuevo login
        carro = self.client.get("/api/carro/").data
        self.assertEqual(len(carro["items"]), 1)
        self.assertEqual(carro["items"][0]["cantidad"], 3)
        self.assertEqual(carro["total"], 300000)
        # Agregar al carro NO descuenta stock
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock, 5)

    def _comprar(self, items):
        for prod, cant in items:
            self.client.post("/api/carro/", {"producto": prod.id, "cantidad": cant})
        return self.client.post("/api/ordenes/checkout/")

    def test_ciclo_completo_stock(self):
        self.auth(self.login("cli", "Cliente12345!")["access"])
        r = self._comprar([(self.p1, 2)])
        self.assertEqual(r.status_code, 201)
        orden_id = r.data["id"]
        self.assertEqual(r.data["estado"], "PENDIENTE")
        self.assertEqual(self.client.get("/api/carro/").data["items"], [])  # carro vaciado
        # Precio congelado: si cambia el catálogo, la orden no cambia.
        Producto.objects.filter(pk=self.p1.pk).update(precio=999999)
        self.assertEqual(self.client.get(f"/api/mis-ordenes/{orden_id}/").data["total"], 200000)
        self.p1.refresh_from_db(); self.assertEqual(self.p1.stock, 5)      # aún sin descuento
        # Pagar -> descuenta
        self.assertEqual(self.client.post(f"/api/ordenes/{orden_id}/pagar/").data["estado"], "PAGADO")
        self.p1.refresh_from_db(); self.assertEqual(self.p1.stock, 3)
        # Cliente no puede cambiar estados
        self.assertEqual(self.client.patch(f"/api/ordenes/{orden_id}/estado/", {"estado": "CANCELADO"}).status_code, 403)
        # Admin cancela -> repone stock
        self.auth(self.login("adm", "Admin12345!")["access"])
        r = self.client.patch(f"/api/ordenes/{orden_id}/estado/", {"estado": "CANCELADO"})
        self.assertEqual(r.data["estado"], "CANCELADO")
        self.p1.refresh_from_db(); self.assertEqual(self.p1.stock, 5)
        # Estado final: no se puede volver atrás
        r = self.client.patch(f"/api/ordenes/{orden_id}/estado/", {"estado": "PAGADO"})
        self.assertEqual(r.status_code, 400)

    def test_pago_rechazado_por_stock_insuficiente_es_atomico(self):
        self.auth(self.login("cli", "Cliente12345!")["access"])
        r = self._comprar([(self.p1, 2), (self.p2, 1)])
        orden_id = r.data["id"]
        # Otro pedido se lleva el único stock de p2 antes de que paguemos.
        Producto.objects.filter(pk=self.p2.pk).update(stock=0)
        r = self.client.post(f"/api/ordenes/{orden_id}/pagar/")
        self.assertEqual(r.status_code, 409)
        # Rollback total: p1 tampoco se descontó y la orden sigue PENDIENTE.
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock, 5)
        self.assertEqual(Orden.objects.get(pk=orden_id).estado, "PENDIENTE")

    def test_admin_marca_entregado_sin_reponer(self):
        self.auth(self.login("cli", "Cliente12345!")["access"])
        orden_id = self._comprar([(self.p1, 1)]).data["id"]
        self.client.post(f"/api/ordenes/{orden_id}/pagar/")
        self.auth(self.login("adm", "Admin12345!")["access"])
        self.assertEqual(self.client.patch(f"/api/ordenes/{orden_id}/estado/", {"estado": "ENTREGADO"}).data["estado"], "ENTREGADO")
        self.p1.refresh_from_db(); self.assertEqual(self.p1.stock, 4)

    def test_cliente_no_ve_ordenes_ajenas(self):
        otro = User.objects.create_user("otro", password="Otro12345!")
        self.auth(self.login("cli", "Cliente12345!")["access"])
        orden_id = self._comprar([(self.p1, 1)]).data["id"]
        self.auth(self.login("otro", "Otro12345!")["access"])
        self.assertEqual(self.client.get(f"/api/mis-ordenes/{orden_id}/").status_code, 404)
        self.assertEqual(self.client.post(f"/api/ordenes/{orden_id}/pagar/").status_code, 404)

    def test_paginas_html_y_docs(self):
        r = self.client.get("/")
        self.assertContains(r, "Bryan Sandoval Morales")
        self.assertEqual(self.client.get("/api/docs/").status_code, 200)
        self.assertEqual(self.client.get("/api/schema/").status_code, 200)
        r = self.client.get("/api/productos/", HTTP_ACCEPT="text/html")
        self.assertContains(r, "Bryan Sandoval Morales")
