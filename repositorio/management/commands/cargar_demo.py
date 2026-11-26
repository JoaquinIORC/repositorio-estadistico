"""Carga datos de ejemplo para mostrar el portal en un computador de desarrollo.

Uso: python manage.py cargar_demo

Se puede correr más de una vez: no duplica nada y no cambia los datos que ya
tienen contenido. Solo funciona con DJANGO_DEBUG=True, para no cargarlo nunca
en el servidor.
"""
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from repositorio.models import MESES, Categoria, Modulo, Reporte

GRUPO_PER_CAPITA = 'Equipo Per Cápita'

# Nombre: (descripción, color, orden)
CATEGORIAS = {
    'Registros y gestión': ('Indicadores oficiales, población inscrita y seguimiento de metas.', 'azul', 10),
    'Listas de espera y garantías': ('Pacientes en espera y casos con garantía.', 'morado', 15),
    'Atención de salud': ('Actividad, agenda y rendimiento de los centros.', 'verde', 20),
    'Prevención y campañas': ('Vacunación y campañas estacionales.', 'naranja', 30),
    'Territorio': ('Información por sector, en mapa.', 'azul', 40),
}

# Nombre: (descripción, categoría, ícono, con enlace de ejemplo, corte, nuevo, orden)
MODULOS = {
    'COMGES': ('Compromisos de gestión.', 'Registros y gestión', 'bandera', True, 'Octubre 2026', False, 40),
    'Lista de espera No GES': ('Consultas y procedimientos pendientes.', 'Listas de espera y garantías', 'lista', True, 'Semana 47', False, 10),
    'GES': ('Garantías explícitas en salud.', 'Listas de espera y garantías', 'escudo', True, 'Noviembre 2026', False, 20),
    'Atenciones de urgencia': ('Consultas por servicio de urgencia.', 'Atención de salud', 'pulso', True, 'Semana 47', False, 30),
    'Campaña de invierno': ('Atenciones respiratorias y vacunas.', 'Prevención y campañas', 'invierno', True, 'Semana 46', True, 10),
    'Visores territoriales': ('Mapas por sector y centro de salud.', 'Territorio', 'mapa', True, '', False, 10),
}

ENLACE_DE_EJEMPLO = 'https://example.org/demo/'

# Documento público del DEIS (MINSAL): en la demo, el reporte REM es este enlace.
MANUAL_REM = (
    'https://repositoriodeis.minsal.cl/ContenidoSitioWeb2020/REM/2026/SERIE/'
    'Manual%20Series%20REM%202026%20SERIE%20A%20BS%20BM%20DV1.2.pdf'
)


def pdf_de_ejemplo(lineas):
    """Un PDF válido de una página con las líneas dadas, sin depender de otras librerías."""
    texto = ['BT', '/F1 14 Tf', '60 780 Td', '20 TL']
    for linea in lineas:
        segura = linea.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        texto.append(f'({segura}) Tj T*')
    texto.append('ET')
    contenido = '\n'.join(texto).encode('cp1252')

    objetos = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] '
        b'/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>',
        b'<< /Length %d >>\nstream\n' % len(contenido) + contenido + b'\nendstream',
    ]
    salida = bytearray(b'%PDF-1.4\n')
    posiciones = []
    for numero, objeto in enumerate(objetos, start=1):
        posiciones.append(len(salida))
        salida += b'%d 0 obj\n' % numero + objeto + b'\nendobj\n'
    inicio_xref = len(salida)
    salida += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objetos) + 1)
    for posicion in posiciones:
        salida += b'%010d 00000 n \n' % posicion
    salida += b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objetos) + 1, inicio_xref)
    return bytes(salida)


class Command(BaseCommand):
    help = 'Carga categorías, módulos, reportes y cuentas de ejemplo (solo en desarrollo).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sin-usuarios', action='store_true',
            help='No crea ni cambia las cuentas de ejemplo.',
        )

    def handle(self, *args, **opciones):
        if not settings.DEBUG:
            raise CommandError(
                'Solo con DJANGO_DEBUG=True: la demo no se carga en el servidor.'
            )

        with transaction.atomic():
            categorias = self.cargar_categorias()
            grupo, _ = Group.objects.get_or_create(name=GRUPO_PER_CAPITA)
            self.completar_modulos_iniciales(categorias, grupo)
            self.cargar_modulos(categorias)
            self.cargar_reportes()
            claves = {} if opciones['sin_usuarios'] else self.cargar_usuarios(grupo)

        self.stdout.write(self.style.SUCCESS('Demo cargada.'))
        self.stdout.write(
            f'Los enlaces de ejemplo apuntan a {ENLACE_DE_EJEMPLO}: cambiarlos en el panel si hace falta.'
        )
        for usuario, (clave, detalle) in claves.items():
            self.stdout.write(f'  {usuario} / {clave}  ({detalle})')
        if claves:
            self.stdout.write('Las claves cambian cada vez que se corre el comando.')

    def cargar_categorias(self):
        categorias = {}
        for nombre, (descripcion, color, orden) in CATEGORIAS.items():
            categorias[nombre], _ = Categoria.objects.get_or_create(
                nombre=nombre,
                defaults={'descripcion': descripcion, 'color': color, 'orden': orden},
            )
        return categorias

    def completar_modulos_iniciales(self, categorias, grupo):
        """Los tres módulos pedidos: solo completa lo que esté vacío."""
        per_capita = Modulo.objects.filter(nombre='Per Cápita Comunal').first()
        if per_capita:
            per_capita.enlace = per_capita.enlace or f'{ENLACE_DE_EJEMPLO}per-capita'
            per_capita.corte = per_capita.corte or 'Noviembre 2026'
            per_capita.categoria = per_capita.categoria or categorias['Registros y gestión']
            per_capita.save()
            per_capita.grupos.add(grupo)

        # Rendimientos queda sin enlace, como está hoy (P-01): se ve "En preparación".
        Modulo.objects.filter(nombre='Rendimientos y Agenda', corte='').update(corte='Semana 47')

    def cargar_modulos(self, categorias):
        for nombre, (descripcion, categoria, icono, con_enlace, corte, nuevo, orden) in MODULOS.items():
            Modulo.objects.get_or_create(
                nombre=nombre,
                defaults={
                    'descripcion': descripcion,
                    'categoria': categorias[categoria],
                    'icono': icono,
                    'enlace': f'{ENLACE_DE_EJEMPLO}{icono}' if con_enlace else '',
                    'corte': corte,
                    'nuevo': nuevo,
                    'orden': orden,
                },
            )

    def cargar_reportes(self):
        modulo = Modulo.objects.filter(nombre='Indicadores IAAPS y REM').first()
        if not modulo:
            return
        autor = get_user_model().objects.filter(is_superuser=True).first() or self.usuario_demo()
        # Un reporte subido como archivo (PDF de ejemplo)...
        if not Reporte.objects.filter(modulo=modulo, titulo='IAAPS comunal').exists():
            reporte = Reporte(modulo=modulo, titulo='IAAPS comunal', anio=2026, mes=11, subido_por=autor)
            contenido = pdf_de_ejemplo([
                f'IAAPS comunal - {MESES[10]} 2026',
                'Reporte de ejemplo para la demostración.',
                'Los datos no son reales.',
            ])
            reporte.archivo.save('ejemplo.pdf', ContentFile(contenido), save=True)
        # ...y otro que es un enlace a un documento publicado.
        Reporte.objects.get_or_create(
            modulo=modulo, titulo='Manual Series REM 2026 - Serie A', anio=2026, mes=11,
            defaults={'enlace': MANUAL_REM, 'subido_por': autor},
        )

    def usuario_demo(self):
        usuario, _ = get_user_model().objects.get_or_create(username='demo-general')
        return usuario

    def cargar_usuarios(self, grupo):
        claves = {}
        cuentas = (
            ('demo-equipo', True, f'del grupo "{GRUPO_PER_CAPITA}": ve Per Cápita'),
            ('demo-general', False, 'sin grupos: no ve Per Cápita'),
        )
        for nombre, en_grupo, detalle in cuentas:
            usuario, _ = get_user_model().objects.get_or_create(username=nombre)
            clave = secrets.token_urlsafe(12)
            usuario.set_password(clave)
            usuario.is_active = True
            usuario.save()
            if en_grupo:
                usuario.groups.add(grupo)
            claves[nombre] = (clave, detalle)
        return claves
