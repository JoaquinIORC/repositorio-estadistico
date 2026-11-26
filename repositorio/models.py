
import re
import uuid
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import (
    FileExtensionValidator,
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models

ENLACE_LOCAL = re.compile(
    r'http://(localhost|127\.0\.0\.1)(:\d+)?(/|$)'
)

MAX_REPORTE_BYTES = 10 * 1024 * 1024

MESES = (
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio',
    'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
)


def validar_enlace(valor):
    """Exige https; en desarrollo también acepta http hacia este mismo computador."""
    if not valor.startswith('https://') and not (
        settings.DEBUG and ENLACE_LOCAL.match(valor)
    ):
        raise ValidationError('Use un enlace que comience con https://.')


def validar_archivo_reporte(archivo):
    """Valida tamaño, extensión y estructura básica real del archivo."""
    if archivo.size > MAX_REPORTE_BYTES:
        raise ValidationError('El archivo no puede superar los 10 MB.')

    extension = Path(archivo.name).suffix.lower()

    if extension not in ('.pdf', '.xlsx'):
        raise ValidationError('Solo se permiten archivos PDF o XLSX.')

    try:
        archivo.seek(0)
        encabezado = archivo.read(8)
        archivo.seek(0)

        if extension == '.pdf':
            if not encabezado.startswith(b'%PDF-'):
                raise ValidationError(
                    'El contenido no corresponde a un PDF válido.'
                )

        elif extension == '.xlsx':
            if not encabezado.startswith(b'PK'):
                raise ValidationError(
                    'El contenido no corresponde a un XLSX válido.'
                )

            with zipfile.ZipFile(archivo) as libro:
                archivos = set(libro.namelist())
                requeridos = {
                    '[Content_Types].xml',
                    'xl/workbook.xml',
                }

                if not requeridos.issubset(archivos):
                    raise ValidationError(
                        'El archivo no tiene la estructura de un XLSX válido.'
                    )

        archivo.seek(0)

    except zipfile.BadZipFile:
        raise ValidationError(
            'El archivo Excel está dañado o no es un XLSX válido.'
        )

    finally:
        archivo.seek(0)


def ruta_reporte_privado(instance, filename):
    """Guarda el archivo con nombre aleatorio, no con el nombre original."""
    extension = Path(filename).suffix.lower()
    return f'reportes/{instance.modulo_id}/{uuid.uuid4().hex}{extension}'


COLORES = (
    ('azul', 'Azul'),
    ('verde', 'Verde'),
    ('morado', 'Morado'),
    ('naranja', 'Naranja'),
)

# Cada valor corresponde a un símbolo de templates/iconos.html.
ICONOS = (
    ('grafico', 'Gráfico'),
    ('documento', 'Documento'),
    ('lista', 'Lista'),
    ('bandera', 'Bandera (metas)'),
    ('personas', 'Personas'),
    ('escritorio', 'Escritorio (agenda)'),
    ('pulso', 'Pulso (urgencia)'),
    ('hospital', 'Hospital'),
    ('vacuna', 'Vacuna'),
    ('invierno', 'Copo de nieve (invierno)'),
    ('mapa', 'Mapa'),
    ('escudo', 'Escudo (garantías)'),
)


class Categoria(models.Model):
    """Agrupa los módulos de la portada en secciones."""

    nombre = models.CharField(max_length=60, unique=True)
    descripcion = models.CharField(
        'descripción', max_length=150, blank=True,
        help_text='Una línea bajo el título de la sección.',
    )
    color = models.CharField(
        max_length=10, choices=COLORES, default='azul',
        help_text='Color de los íconos de sus módulos.',
    )
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['orden', 'nombre']
        verbose_name = 'categoría'
        verbose_name_plural = 'categorías'

    def __str__(self):
        return self.nombre


class ModuloQuerySet(models.QuerySet):
    def visibles_para(self, usuario):
        """Módulos sin grupos, más los de algún grupo del usuario. Un superusuario ve todos."""
        if usuario.is_superuser:
            return self
        return self.filter(
            models.Q(grupos__isnull=True) | models.Q(grupos__in=usuario.groups.all())
        ).distinct()


class Modulo(models.Model):
    """Una herramienta del repositorio. Se agregan desde el panel."""

    objects = ModuloQuerySet.as_manager()

    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.CharField('descripción', max_length=200, blank=True)
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='modulos',
        verbose_name='categoría',
        help_text='Sin categoría, aparece al final, en "Otras herramientas".',
    )
    icono = models.CharField('ícono', max_length=12, choices=ICONOS, default='grafico')
    nuevo = models.BooleanField(
        default=False, help_text='Muestra la etiqueta "Nuevo" en la portada.',
    )
    enlace = models.URLField(
        max_length=500,
        blank=True,
        validators=[validar_enlace],
        help_text=(
            'Sin enlace, el módulo aparece como "En preparación". En Power BI '
            'use un informe compartido con cuentas institucionales: un enlace '
            '"Publicar en la web" (view?r=) lo puede abrir cualquiera que lo '
            'tenga, aunque aquí se pida sesión.'
        ),
    )
    corte = models.CharField(
        'último corte',
        max_length=40,
        blank=True,
        help_text=(
            'Por ejemplo: Noviembre 2026 o Semana 47. Si el módulo tiene '
            'reportes cargados, se muestra el período del más reciente.'
        ),
    )
    grupos = models.ManyToManyField(
        'auth.Group',
        blank=True,
        related_name='modulos',
        help_text=(
            'Vacío: lo ven todos los usuarios. Con grupos: solo sus miembros '
            '(y los superusuarios). Se aplica también a sus reportes.'
        ),
    )
    orden = models.PositiveSmallIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['orden', 'nombre']
        verbose_name = 'módulo'
        verbose_name_plural = 'módulos'

    def __str__(self):
        return self.nombre


class Reporte(models.Model):
    """Archivo estadístico, o enlace a un documento publicado, de un módulo y período."""

    modulo = models.ForeignKey(
        Modulo,
        on_delete=models.CASCADE,
        related_name='reportes',
        verbose_name='módulo',
    )
    titulo = models.CharField(max_length=150)
    anio = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(2000), MaxValueValidator(2100)]
    )
    mes = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    archivo = models.FileField(
        blank=True,
        upload_to=ruta_reporte_privado,
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf', 'xlsx']),
            validar_archivo_reporte,
        ],
        help_text=(
            '⚠️ No subir archivos con RUT, nombres ni datos de personas. '
            'Dejar vacío si el reporte es un enlace.'
        ),
    )
    enlace = models.URLField(
        max_length=500,
        blank=True,
        validators=[validar_enlace],
        help_text=(
            'En vez de subir un archivo: enlace https a un documento ya publicado, '
            'por ejemplo un manual del MINSAL. Se abre en otra pestaña.'
        ),
    )
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='reportes_subidos',
    )
    subido_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-anio', '-mes', '-subido_en', 'titulo']
        constraints = [
            models.UniqueConstraint(
                fields=['modulo', 'titulo', 'anio', 'mes'],
                name='reporte_modulo_titulo_periodo_unico',
            ),
        ]
        verbose_name = 'reporte'
        verbose_name_plural = 'reportes'

    def __str__(self):
        return f'{self.modulo} — {self.titulo} ({self.periodo})'

    def clean(self):
        super().clean()
        if bool(self.archivo) == bool(self.enlace):
            raise ValidationError('Suba un archivo o escriba un enlace, pero no ambos.')

    @property
    def periodo(self):
        """Mes y año en palabras, como lo muestra el sello: Noviembre 2026."""
        return f'{MESES[self.mes - 1]} {self.anio}'


class Acceso(models.Model):
    """Quién abrió qué y cuándo. Lo escribe el sistema; en el panel solo se consulta."""

    ABRIR = 'abrir'
    REPORTES = 'reportes'
    DESCARGA = 'descarga'
    TIPOS = (
        (ABRIR, 'Abrió el enlace'),
        (REPORTES, 'Vio la lista de reportes'),
        (DESCARGA, 'Descargó un reporte'),
    )

    fecha = models.DateTimeField(auto_now_add=True, db_index=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='accesos',
    )
    # Los nombres se copian como texto: el registro se mantiene aunque después
    # se borre o renombre la cuenta, el módulo o el reporte.
    nombre_usuario = models.CharField('usuario', max_length=150)
    tipo = models.CharField(max_length=10, choices=TIPOS)
    modulo = models.ForeignKey(
        Modulo, on_delete=models.SET_NULL, null=True, related_name='accesos',
        verbose_name='módulo',
    )
    detalle = models.CharField(max_length=250)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'acceso registrado'
        verbose_name_plural = 'accesos registrados'

    def __str__(self):
        return f'{self.nombre_usuario}: {self.get_tipo_display()} ({self.detalle})'

    @classmethod
    def anotar(cls, usuario, tipo, modulo, detalle):
        return cls.objects.create(
            usuario=usuario,
            nombre_usuario=usuario.get_username(),
            tipo=tipo,
            modulo=modulo,
            detalle=detalle[:250],
        )


class IntentoFallido(models.Model):
    """Un ingreso con clave incorrecta. Sirve para bloquear a quien prueba claves (ver ingreso.py)."""

    nombre_usuario = models.CharField('usuario', max_length=150, db_index=True)
    ip = models.GenericIPAddressField('IP', null=True)
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'intento fallido de ingreso'
        verbose_name_plural = 'intentos fallidos de ingreso'

    def __str__(self):
        return f'{self.nombre_usuario} desde {self.ip}'
