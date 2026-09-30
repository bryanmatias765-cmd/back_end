"""
SEÑALES
Cada vez que se crea un usuario se le genera automáticamente su Perfil (rol)
y su Carro, así el carro 1 a 1 siempre existe en PostgreSQL.
"""
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Carro, Perfil


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def crear_perfil_y_carro(sender, instance, created, **kwargs):
    if created:
        # Los superusuarios/staff nacen como ADMINISTRADOR; el resto como CLIENTE.
        rol = Perfil.Rol.ADMINISTRADOR if instance.is_staff else Perfil.Rol.CLIENTE
        Perfil.objects.create(user=instance, rol=rol)
        Carro.objects.create(user=instance)
