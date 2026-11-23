import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

ENLACE_LOCAL = re.compile(r'http://(localhost|127\.0\.0\.1)(:\d+)?(/|$)')


def validar_enlace(valor):
    """Exige https; en desarrollo también acepta http hacia este mismo computador."""
    if not valor.startswith('https://') and not (settings.DEBUG and ENLACE_LOCAL.match(valor)):
        raise ValidationError('Use un enlace que comience con https://.')


class Modulo(models.Model):
    """Una herramienta del repositorio. Se agregan desde el panel."""

    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.CharField('descripción', max_length=200, blank=True)
    enlace = models.URLField(
        max_length=500,
        blank=True,
        validators=[validar_enlace],
        help_text=(
            'Sin enlace, el módulo aparece como "En preparación". En Power BI use un informe '
            'compartido con cuentas institucionales: un enlace "Publicar en la web" (view?r=) '
            'lo puede abrir cualquiera que lo tenga, aunque aquí se pida sesión.'
        ),
    )
    corte = models.CharField(
        'último corte', max_length=40, blank=True,
        help_text='Por ejemplo: Noviembre 2026 o Semana 47.',
    )
    orden = models.PositiveSmallIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['orden', 'nombre']
        verbose_name = 'módulo'
        verbose_name_plural = 'módulos'

    def __str__(self):
        return self.nombre
