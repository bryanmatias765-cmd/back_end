# Tienda de Hardware y Componentes PC — EVA-2 Desarrollo Backend

API REST con **Django REST Framework + PostgreSQL + JWT** (Proyecto 1: Retail).
Alumno: Bryan Sandoval Morales · Sección: _(completar)_ · Año: 2026

## 1. Instalación (Windows + VS Code)

1. Instalar **PostgreSQL** (https://www.postgresql.org/download/) y recordar la contraseña del usuario `postgres`.
2. Crear la base de datos (en **pgAdmin** o en la terminal `psql -U postgres`):
   ```sql
   CREATE DATABASE tienda_hardware;
   ```
3. En la carpeta del proyecto, abrir la terminal de VS Code:
   ```powershell
   python -m venv env
   .\env\Scripts\activate
   python.exe -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
   (Si PowerShell bloquea la activación: `Set-ExecutionPolicy Unrestricted -Scope Process`)
4. Crear el archivo `.env` copiando `.env.example` y poner tu contraseña de PostgreSQL y tu sección:
   ```powershell
   copy .env.example .env
   ```
5. Migrar, cargar datos de ejemplo y levantar el servidor:
   ```powershell
   python manage.py migrate
   python manage.py cargar_datos
   python manage.py runserver
   ```

Usuarios de prueba: `admin_ti / Admin12345!` (ADMINISTRADOR) y `cliente1 / Cliente12345!` (CLIENTE).

## 2. Rutas principales

| Rol | Método y ruta | Descripción |
|---|---|---|
| Público | `GET /` | Vista HTML con catálogo y footer del alumno |
| Público | `GET /api/productos/` `GET /api/categorias/` | Catálogo (filtros y búsqueda) |
| Público | `POST /api/auth/registro/` | Crea un CLIENTE |
| Público | `POST /api/auth/login/` | Devuelve `access` + `refresh` (claim `rol`) |
| Autenticado | `POST /api/auth/refresh/` `POST /api/auth/logout/` | Renovar token / invalidar refresh |
| Cliente | `GET/POST/DELETE /api/carro/` | Ver, agregar (suma si existe) y vaciar carro |
| Cliente | `PATCH/DELETE /api/carro/items/{producto_id}/` | Cambiar cantidad / quitar ítem |
| Cliente | `POST /api/ordenes/checkout/` | Genera Orden PENDIENTE (precios congelados) |
| Cliente | `POST /api/ordenes/{id}/pagar/` | Pago simulado: valida y descuenta stock → PAGADO |
| Cliente | `GET /api/mis-ordenes/` | Historial propio |
| Admin | `POST/PUT/PATCH/DELETE /api/productos/` (y categorías) | Gestión de catálogo |
| Admin | `PATCH /api/ordenes/{id}/estado/` | `ENTREGADO` / `CANCELADO` (repone stock) |
| Admin | `GET /api/ordenes/?estado=PAGADO` | Todas las órdenes |
| Docs | `GET /api/docs/` | Swagger / OpenAPI |

Filtros de productos: `?categoria=2&precio_min=50000&precio_max=200000&marca=amd&en_stock=true&search=ryzen&ordering=-precio`

## 3. Probar en Swagger
1. `/api/docs/` → `POST /api/auth/login/` con `cliente1` → copiar `access`.
2. Botón **Authorize** → pegar `Bearer <access>`.
3. Agregar productos al carro → checkout → pagar → revisar stock en `/api/productos/`.
4. Login como `admin_ti` y cancelar la orden → el stock vuelve.

## 4. Estructura
- `api/models.py` modelos (CHOICES en `Perfil.Rol` y `Orden.Estado`)
- `api/services.py` checkout + transacciones + stock (`transaction.atomic`, `select_for_update`)
- `api/serializers.py` JWT con claim `rol`, validaciones
- `api/permissions.py` permisos por rol · `api/filters.py` django-filter
- `api/views.py` / `api/urls.py` endpoints · `api/tests.py` pruebas (`python manage.py test`)

## 5. Subir a GitHub (antes de la hora límite)
```powershell
git init
git add .
git commit -m "EVA-2 Backend: Tienda de Hardware"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/tienda-hardware.git
git push -u origin main
```
El `.gitignore` excluye `env/` y `.env` (no subas contraseñas).
