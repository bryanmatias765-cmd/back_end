"""
PERMISOS PERSONALIZADOS POR ROL
El rol se lee desde el Perfil del usuario autenticado (el mismo valor que
viaja como claim "rol" dentro del JWT).
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import Perfil


def es_admin(user):
    return bool(
        user and user.is_authenticated
        and hasattr(user, "perfil") and user.perfil.rol == Perfil.Rol.ADMINISTRADOR
    )


class EsAdministrador(BasePermission):
    """Solo usuarios con rol ADMINISTRADOR."""
    message = "Se requiere rol de Administrador."

    def has_permission(self, request, view):
        return es_admin(request.user)


class LecturaPublicaEscrituraAdmin(BasePermission):
    """Catálogo: GET/HEAD/OPTIONS para todos; POST/PUT/PATCH/DELETE solo Administrador."""
    message = "Solo un Administrador puede modificar el catálogo."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return es_admin(request.user)
