
import tempfile
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Categoria, Modulo, Reporte, validar_archivo_reporte

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

    def test_con_clave_incorrecta_anuncia_el_error(self):
        respuesta = self.client.post(reverse('login'), {'username': 'ana', 'password': 'otra'})

        self.assertContains(respuesta, 'role="alert"')

    def test_el_ingreso_no_muestra_la_barra_superior(self):
        self.assertNotContains(self.client.get(reverse('login')), 'class="barra"')

    def test_el_ingreso_dice_en_que_sistema_se_entra(self):
        self.assertContains(
            self.client.get(reverse('login')),
            '<p class="ingreso-marca">Repositorio Estadístico</p>',
        )

    def test_el_aviso_de_mayusculas_queda_en_la_pagina(self):
        # Vacío pero presente: el lector de pantalla lo anuncia cuando cambia.
        self.assertContains(
            self.client.get(reverse('login')),
            '<p class="aviso-mayus" id="aviso-mayus" aria-live="polite"></p>',
        )

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

    def test_el_sello_muestra_cada_corte_por_separado(self):
        Modulo.objects.create(nombre='Tablero A', enlace=ENLACE, corte='Semana 47')
        Modulo.objects.create(nombre='Tablero B', enlace=ENLACE, corte='Octubre 2026')

        respuesta = self.abrir()

        self.assertContains(respuesta, '<li>Tablero A: Semana 47</li>')
        self.assertContains(respuesta, '<li>Tablero B: Octubre 2026</li>')

    def test_el_enlace_avisa_que_abre_otra_pestana(self):
        Modulo.objects.create(nombre='Tablero nuevo', enlace=ENLACE)

        self.assertContains(self.abrir(), '(se abre en otra pestaña)', count=1)

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


class CategoriaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user('ana')
        # Se parte sin los módulos iniciales, para controlar cada caso.
        Modulo.objects.all().delete()
        Categoria.objects.all().delete()

    def abrir(self):
        self.client.force_login(self.usuario)
        return self.client.get(reverse('inicio'))

    def test_agrupa_por_categoria_en_su_orden(self):
        atencion = Categoria.objects.create(nombre='Atención de salud', orden=20)
        registros = Categoria.objects.create(nombre='Registros y gestión', orden=10)
        Modulo.objects.create(nombre='Urgencia', categoria=atencion, enlace=ENLACE)
        Modulo.objects.create(nombre='REM', categoria=registros, enlace=ENLACE)

        contenido = self.abrir().content.decode()

        self.assertLess(contenido.index('Registros y gestión</h2>'), contenido.index('Atención de salud</h2>'))
        self.assertLess(contenido.index('<b>REM</b>'), contenido.index('Atención de salud</h2>'))
        self.assertGreater(contenido.index('<b>Urgencia</b>'), contenido.index('Atención de salud</h2>'))

    def test_sin_categoria_va_al_final(self):
        registros = Categoria.objects.create(nombre='Registros y gestión')
        Modulo.objects.create(nombre='REM', categoria=registros, enlace=ENLACE)
        Modulo.objects.create(nombre='Suelto', enlace=ENLACE)

        contenido = self.abrir().content.decode()

        self.assertLess(contenido.index('Otras herramientas</h2>'), contenido.index('<b>Suelto</b>'))
        self.assertLess(contenido.index('<b>REM</b>'), contenido.index('Otras herramientas</h2>'))

    def test_sin_ninguna_categoria_no_muestra_titulos(self):
        Modulo.objects.create(nombre='Suelto', enlace=ENLACE)

        respuesta = self.abrir()

        self.assertContains(respuesta, '<b>Suelto</b>')
        self.assertNotContains(respuesta, '<h2')

    def test_una_categoria_sin_modulos_activos_no_aparece(self):
        vacia = Categoria.objects.create(nombre='Campañas')
        Modulo.objects.create(nombre='Invierno', categoria=vacia, activo=False)
        Modulo.objects.create(nombre='Suelto', enlace=ENLACE)

        self.assertNotContains(self.abrir(), 'Campañas')

    def test_usa_el_color_de_la_categoria_y_el_icono_del_modulo(self):
        verde = Categoria.objects.create(nombre='Atención de salud', color='verde')
        Modulo.objects.create(nombre='Urgencia', categoria=verde, icono='pulso', enlace=ENLACE)

        respuesta = self.abrir()

        self.assertContains(respuesta, 'class="card color-verde"')
        self.assertContains(respuesta, '<use href="#i-pulso"/>')

    def test_la_etiqueta_nuevo(self):
        Modulo.objects.create(nombre='Campaña de invierno', enlace=ENLACE, nuevo=True)
        Modulo.objects.create(nombre='REM', enlace=ENLACE)

        self.assertContains(self.abrir(), '<span class="nuevo">Nuevo</span>', count=1)

    def test_el_buscador_revisa_nombre_descripcion_y_categoria(self):
        registros = Categoria.objects.create(nombre='Registros y gestión', descripcion='Metas')
        Modulo.objects.create(
            nombre='REM', descripcion='Registro Estadístico Mensual', categoria=registros, enlace=ENLACE,
        )

        respuesta = self.abrir()

        self.assertContains(respuesta, 'id="q" type="search"')
        self.assertContains(respuesta, 'data-buscar="REM Registro Estadístico Mensual Registros y gestión Metas"')


class AccesoPorGrupoTests(TestCase):
    @classmethod
    def setUpClass(cls):
        # El reporte de prueba se guarda en una carpeta temporal que se borra al terminar.
        cls.directorio_media = tempfile.TemporaryDirectory()
        cls.override_media = override_settings(MEDIA_ROOT=Path(cls.directorio_media.name))
        cls.override_media.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.override_media.disable()
        cls.directorio_media.cleanup()

    @classmethod
    def setUpTestData(cls):
        Modulo.objects.all().delete()
        cls.equipo = Group.objects.create(name='Equipo Per Cápita')
        cls.comun = get_user_model().objects.create_user('comun')
        cls.miembro = get_user_model().objects.create_user('miembro')
        cls.miembro.groups.add(cls.equipo)
        cls.admin = get_user_model().objects.create_superuser('jefe')

        cls.abierto = Modulo.objects.create(nombre='Abierto', enlace=ENLACE, corte='Semana 47')
        cls.restringido = Modulo.objects.create(
            nombre='Restringido', descripcion='Solo el equipo', corte='Noviembre 2026',
        )
        cls.restringido.grupos.add(cls.equipo)
        cls.reporte = Reporte.objects.create(
            modulo=cls.restringido, titulo='Informe', anio=2026, mes=11, subido_por=cls.admin,
            archivo=SimpleUploadedFile('r.pdf', b'%PDF-1.4 prueba', content_type='application/pdf'),
        )

    def portada(self, usuario):
        self.client.force_login(usuario)
        return self.client.get(reverse('inicio'))

    def test_quien_no_es_del_grupo_no_ve_el_modulo_ni_su_corte(self):
        respuesta = self.portada(self.comun)

        self.assertContains(respuesta, '<b>Abierto</b>')
        self.assertNotContains(respuesta, 'Restringido')
        self.assertNotContains(respuesta, 'Noviembre 2026')

    def test_un_miembro_del_grupo_lo_ve(self):
        respuesta = self.portada(self.miembro)

        self.assertContains(respuesta, '<b>Restringido</b>')
        self.assertContains(respuesta, '<b>Abierto</b>')

    def test_un_superusuario_ve_todo(self):
        self.assertContains(self.portada(self.admin), '<b>Restringido</b>')

    def test_un_modulo_con_dos_grupos_aparece_una_vez(self):
        otro = Group.objects.create(name='Otro equipo')
        self.restringido.grupos.add(otro)
        self.miembro.groups.add(otro)

        self.assertContains(self.portada(self.miembro), '<b>Restringido</b>', count=1)

    def test_sin_acceso_la_lista_y_la_descarga_no_existen(self):
        self.client.force_login(self.comun)

        lista = self.client.get(reverse('lista_reportes', args=[self.restringido.id]))
        descarga = self.client.get(reverse('descargar_reporte', args=[self.reporte.id]))

        self.assertEqual(lista.status_code, 404)
        self.assertEqual(descarga.status_code, 404)

    def test_un_miembro_descarga_el_reporte(self):
        self.client.force_login(self.miembro)

        respuesta = self.client.get(reverse('descargar_reporte', args=[self.reporte.id]))

        try:
            self.assertEqual(respuesta.status_code, 200)
        finally:
            respuesta.close()


class ModulosInicialesTests(TestCase):
    def test_los_tres_modulos_parten_en_su_categoria(self):
        esperado = {
            'Per Cápita Comunal': 'Registros y gestión',
            'Indicadores IAAPS y REM': 'Registros y gestión',
            'Rendimientos y Agenda': 'Atención de salud',
        }
        for nombre, categoria in esperado.items():
            with self.subTest(nombre=nombre):
                self.assertEqual(Modulo.objects.get(nombre=nombre).categoria.nombre, categoria)


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

    def test_el_sello_muestra_el_periodo_del_reporte_mas_reciente(self):
        self.modulo.corte = 'Semana 40'
        self.modulo.save()
        self.crear_reporte(titulo='Octubre', mes=10)
        self.crear_reporte(titulo='Noviembre', mes=11)
        self.client.force_login(self.usuario)

        respuesta = self.client.get(reverse('inicio'))

        self.assertContains(respuesta, '<li>Modulo de prueba reportes: Noviembre 2026</li>')
        self.assertNotContains(respuesta, 'Semana 40')

    def test_la_portada_lleva_a_la_lista_de_reportes(self):
        self.crear_reporte()
        self.client.force_login(self.usuario)

        respuesta = self.client.get(reverse('inicio'))

        self.assertContains(respuesta, f'href="{reverse("lista_reportes", args=[self.modulo.id])}"')
        self.assertContains(respuesta, 'Ver reportes')

    def test_no_descarga_reportes_de_un_modulo_desactivado(self):
        reporte = self.crear_reporte()
        self.modulo.activo = False
        self.modulo.save()
        self.client.force_login(self.usuario)

        respuesta = self.client.get(reverse('descargar_reporte', args=[reporte.id]))

        self.assertEqual(respuesta.status_code, 404)

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
