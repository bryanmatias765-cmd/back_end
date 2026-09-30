"""Context processor: deja disponibles en TODOS los templates los datos del alumno."""
from django.conf import settings


def datos_alumno(request):
    return {
        "ALUMNO_NOMBRE": settings.ALUMNO_NOMBRE,
        "ALUMNO_SECCION": settings.ALUMNO_SECCION,
        "ALUMNO_ANIO": settings.ALUMNO_ANIO,
    }
