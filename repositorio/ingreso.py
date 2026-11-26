"""Límite de intentos de ingreso, en el portal y en el panel.

Nginx ya limita los ingresos por IP, pero en una oficina todos salen con la misma
IP: ese límite es de la oficina, no de cada cuenta. Aquí se cuenta por cuenta y
equipo: tras MAX_FALLAS claves incorrectas en VENTANA, esa cuenta queda bloqueada
desde ese equipo hasta que pase la ventana, aunque luego se escriba la clave
correcta. Otra persona en la misma oficina puede seguir entrando con su cuenta.
"""
import ipaddress
from datetime import timedelta

from django.conf import settings
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import IntentoFallido

MAX_FALLAS = 5
VENTANA = timedelta(minutes=15)

MENSAJE_BLOQUEO = (
    'Hubo demasiados intentos fallidos con esta cuenta. Espere 15 minutos e intente '
    'de nuevo, o pida ayuda al administrador.'
)


def _ip_valida(valor):
    try:
        return str(ipaddress.ip_address((valor or '').strip()))
    except ValueError:
        return None


def ip_de(request):
    """IP de quien ingresa.

    En el servidor, Gunicorn solo escucha en 127.0.0.1 y le habla Nginx, que pone
    X-Real-IP con la IP real (y reemplaza la que mande el navegador). Sin Nginx
    (en desarrollo) se usa la conexión directa.
    """
    if request is None:
        return None
    if not settings.DEBUG:
        real = _ip_valida(request.META.get('HTTP_X_REAL_IP'))
        if real:
            return real
    return _ip_valida(request.META.get('REMOTE_ADDR'))


def _fallas_recientes(nombre, ip):
    return IntentoFallido.objects.filter(
        nombre_usuario=nombre, ip=ip, fecha__gte=timezone.now() - VENTANA,
    )


class LimiteDeIntentos:
    """Se mezcla con el formulario de ingreso de Django: revisa el bloqueo antes de probar la clave."""

    def clean(self):
        nombre = (self.cleaned_data.get('username') or '').strip().lower()
        ip = ip_de(self.request)
        # Mismo mensaje exista o no la cuenta: no revela qué usuarios hay.
        if nombre and _fallas_recientes(nombre, ip).count() >= MAX_FALLAS:
            raise ValidationError(MENSAJE_BLOQUEO, code='bloqueado')
        try:
            datos = super().clean()
        except ValidationError as error:
            if nombre and error.code == 'invalid_login':
                IntentoFallido.objects.create(nombre_usuario=nombre, ip=ip)
                # Los registros viejos ya no sirven para el bloqueo.
                IntentoFallido.objects.filter(fecha__lt=timezone.now() - timedelta(days=1)).delete()
            raise
        # Entró: sus fallas anteriores desde este equipo dejan de contar.
        _fallas_recientes(nombre, ip).delete()
        return datos


class FormularioIngreso(LimiteDeIntentos, AuthenticationForm):
    pass


class FormularioIngresoPanel(LimiteDeIntentos, AdminAuthenticationForm):
    pass
