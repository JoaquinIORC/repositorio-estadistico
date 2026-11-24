
import tempfile
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Modulo, Reporte, validar_archivo_reporte

ENLACE = 'https://app.powerbi.com/groups/me/reports/abc'


class AccesoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            'ana', password='clave-de-prueba-9'
        )

    def test_sin_sesion_lleva_al_ingreso(self):
        respuesta = self.client.get(reverse('inicio'))
        self.assertRedirects(respuesta, f'{reverse("login")}?next=/')

    def test_con_clave_correcta_entra(self):
        respuesta = self.client.post(
            reverse('login'),
            {'username': 'ana', 'password': 'clave-de-prueba-9'},
            follow=True,
        )
        self.assertContains(respuesta, 'Información disponible')

    def test_con_clave_incorrecta_no_entra(self):
        self.client.post(
            reverse('login'),
            {'username': 'ana', 'password': 'otra'},
        )
        self.assertEqual(self.client.get(reverse('inicio')).status_code, 302)

    def test_un_usuario_comun_no_administra(self):
        self.client.force_login(self.usuario)
        self.assertNotContains(self.client.get(reverse('inicio')), 'Administrar')
        self.assertEqual(
            self.client.get('/admin/repositorio/modulo/').status_code, 302
        )

    def test_sus_cookies_no_chocan_con_las_de_percapitados(self):
        self.assertNotEqual(settings.SESSION_COOKIE_NAME, 'sessionid')
        self.assertNotEqual(settings.CSRF_COOKIE_NAME, 'csrftoken')


class PortadaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user('ana')

    def abrir(self):
        self.client.force_login(self.usuario)
        return self.client.get(reverse('inicio'))

    def test_parte_con_los_tres_modulos_en_preparacion(self):
        respuesta = self.abrir()

        for nombre in (
            'Per Cápita Comunal',
            'Rendimientos y Agenda',
            'Indicadores IAAPS y REM',
        ):
            self.assertContains(respuesta, nombre)

        self.assertContains(respuesta, 'En preparación', count=3)
        self.assertContains(respuesta, 'todavía no hay cortes informados')

    def test_un_modulo_nuevo_aparece_con_su_enlace_y_corte(self):
        Modulo.objects.create(
            nombre='Tablero nuevo', enlace=ENLACE, corte='Semana 47'
        )
        respuesta = self.abrir()

        self.assertContains(respuesta, 'Tablero nuevo: Semana 47')
        self.assertContains(
            respuesta,
            f'href="{ENLACE}" target="_blank" rel="noopener noreferrer"',
        )

    def test_el_sello_dice_si_falta_el_corte(self):
        Modulo.objects.create(nombre='Tablero nuevo', enlace=ENLACE)
        self.assertContains(self.abrir(), 'Tablero nuevo: sin informar')

    def test_un_modulo_inactivo_no_aparece(self):
        Modulo.objects.create(
            nombre='Tablero oculto', enlace=ENLACE, activo=False
        )
        self.assertNotContains(self.abrir(), 'Tablero oculto')

    def test_el_enlace_debe_ser_https(self):
        for enlace in ('http://app.powerbi.com/x', 'javascript:alert(1)'):
            with self.subTest(enlace=enlace), self.assertRaises(ValidationError):
                Modulo(nombre='Inseguro', enlace=enlace).full_clean()

    @override_settings(DEBUG=True)
    def test_en_desarrollo_acepta_http_solo_hacia_este_computador(self):
        Modulo(nombre='Local', enlace='http://localhost:8000/').full_clean()
        Modulo(nombre='Local', enlace='http://127.0.0.1:8000').full_clean()

        for enlace in (
            'http://localhost.malo.cl/',
            'http://localhost@malo.cl/',
            'http://malo.cl/',
        ):
            with self.subTest(enlace=enlace), self.assertRaises(ValidationError):
                Modulo(nombre='Inseguro', enlace=enlace).full_clean()

    def test_fuera_de_desarrollo_no_acepta_localhost(self):
        with self.assertRaises(ValidationError):
            Modulo(nombre='Local', enlace='http://localhost:8000/').full_clean()


class ReporteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            'ana', password='clave-de-prueba-9'
        )
        cls.modulo = Modulo.objects.create(
            nombre='Modulo de prueba reportes'
        )

    def setUp(self):
        self.directorio_temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.directorio_temporal.cleanup)

        self.override_media = override_settings(
            MEDIA_ROOT=Path(self.directorio_temporal.name)
        )
        self.override_media.enable()
        self.addCleanup(self.override_media.disable)

    def crear_reporte(self, archivo=None, **kwargs):
        if archivo is None:
            archivo = SimpleUploadedFile(
                'reporte.pdf',
                b'%PDF-1.4 contenido de prueba',
                content_type='application/pdf',
            )

        valores = {
            'modulo': self.modulo,
            'titulo': 'Informe mensual',
            'anio': 2026,
            'mes': 11,
            'archivo': archivo,
            'subido_por': self.usuario,
        }
        valores.update(kwargs)
        return Reporte.objects.create(**valores)

    def test_usuario_anonimo_no_puede_ver_reportes(self):
        respuesta = self.client.get(
            reverse('lista_reportes', args=[self.modulo.id])
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertRedirects(
            respuesta,
            f'{reverse("login")}?next={reverse("lista_reportes", args=[self.modulo.id])}',
        )

    def test_usuario_anonimo_no_puede_descargar(self):
        reporte = self.crear_reporte()
        respuesta = self.client.get(
            reverse('descargar_reporte', args=[reporte.id])
        )
        self.assertEqual(respuesta.status_code, 302

)
        respuesta.close()

    def test_usuario_autenticado_puede_ver_listado(self):
        self.crear_reporte()
        self.client.force_login(self.usuario)

        respuesta = self.client.get(
            reverse('lista_reportes', args=[self.modulo.id])
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Informe mensual')

    def test_usuario_autenticado_puede_descargar(self):
        reporte = self.crear_reporte()
        self.client.force_login(self.usuario)

        respuesta = self.client.get(
            reverse('descargar_reporte', args=[reporte.id])
        )

        try:
            self.assertEqual(respuesta.status_code, 200)
            self.assertTrue(respuesta.streaming)
            self.assertIn('attachment', respuesta['Content-Disposition'])
            self.assertIn(
                'informe-mensual-11-2026.pdf',
                respuesta['Content-Disposition'],
            )
        finally:
            respuesta.close()

    def test_rechaza_extension_no_permitida(self):
        archivo = SimpleUploadedFile(
            'reporte.txt', b'texto', content_type='text/plain'
        )
        with self.assertRaises(ValidationError):
            validar_archivo_reporte(archivo)

    def test_rechaza_pdf_falso(self):
        archivo = SimpleUploadedFile(
            'reporte.pdf', b'no es un pdf', content_type='application/pdf'
        )
        with self.assertRaises(ValidationError):
            validar_archivo_reporte(archivo)

    def test_rechaza_excel_falso(self):
        archivo = SimpleUploadedFile(
            'reporte.xlsx',
            b'no es un excel',
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        with self.assertRaises(ValidationError):
            validar_archivo_reporte(archivo)

    def test_rechaza_archivo_mayor_a_10_mb(self):
        archivo = SimpleUploadedFile(
            'reporte.pdf',
            b'%PDF-' + (b'0' * (10 * 1024 * 1024)),
            content_type='application/pdf',
        )
        with self.assertRaises(ValidationError):
            validar_archivo_reporte(archivo)

    def test_reporte_duplicado_no_se_acepta(self):
        self.crear_reporte()
        duplicado = Reporte(
            modulo=self.modulo,
            titulo='Informe mensual',
            anio=2026,
            mes=11,
            archivo=SimpleUploadedFile(
                'otro.pdf',
                b'%PDF-1.4 prueba',
                content_type='application/pdf',
            ),
            subido_por=self.usuario,
        )
        with self.assertRaises(ValidationError):
            duplicado.full_clean()
