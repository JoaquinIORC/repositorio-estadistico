from django.core.validators import URLValidator
from django.db import models


class Modulo(models.Model):
    """Una herramienta del repositorio. Se agregan desde el panel."""

    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.CharField('descripción', max_length=200, blank=True)
    enlace = models.URLField(
        max_length=500,
        blank=True,
        validators=[URLValidator(schemes=['https'], message='Use un enlace que comience con https://.')],
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
