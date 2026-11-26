
import re
import tempfile
from datetime import timedelta
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import CommandError, call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Acceso, Categoria, IntentoFallido, Modulo, Reporte, validar_archivo_reporte
from .remoto import MAX_BYTES, EnlaceNoPermitido, _SoloHttps, traer_pdf, verificar_destino

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

    def test_los_reportes_subidos_no_los_leen_otras_cuentas(self):
        self.assertEqual(settings.FILE_UPLOAD_PERMISSIONS, 0o600)
        self.assertEqual(settings.FILE_UPLOAD_DIRECTORY_PERMISSIONS, 0o700)

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

        modulo = Modulo.objects.get(nombre='Tablero nuevo')
        self.assertContains(respuesta, 'Tablero nuevo: Semana 47')
        # La tarjeta pasa por el registro de accesos, que lleva al enlace.
        self.assertContains(
            respuesta,
            f'href="{reverse("abrir_modulo", args=[modulo.id])}" target="_blank" rel="noopener noreferrer"',
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


class RegistroDeAccesosTests(TestCase):
    @classmethod
    def setUpClass(cls):
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
        cls.usuario = get_user_model().objects.create_user('ana')
        cls.con_enlace = Modulo.objects.create(nombre='Tablero', enlace=ENLACE)
        cls.con_reportes = Modulo.objects.create(nombre='Informes')
        cls.reporte = Reporte.objects.create(
            modulo=cls.con_reportes, titulo='IAAPS', anio=2026, mes=11, subido_por=cls.usuario,
            archivo=SimpleUploadedFile('r.pdf', b'%PDF-1.4 prueba', content_type='application/pdf'),
        )

    def setUp(self):
        self.client.force_login(self.usuario)

    def test_abrir_anota_y_lleva_al_enlace(self):
        respuesta = self.client.get(reverse('abrir_modulo', args=[self.con_enlace.id]))

        self.assertRedirects(respuesta, ENLACE, fetch_redirect_response=False)
        acceso = Acceso.objects.get()
        self.assertEqual(
            (acceso.usuario, acceso.nombre_usuario, acceso.tipo, acceso.modulo, acceso.detalle),
            (self.usuario, 'ana', Acceso.ABRIR, self.con_enlace, 'Tablero'),
        )

    def test_la_lista_y_la_descarga_se_anotan(self):
        self.client.get(reverse('lista_reportes', args=[self.con_reportes.id]))
        self.client.get(reverse('descargar_reporte', args=[self.reporte.id])).close()

        self.assertEqual(
            list(Acceso.objects.order_by('fecha', 'id').values_list('tipo', 'detalle')),
            [(Acceso.REPORTES, 'Informes'), (Acceso.DESCARGA, 'Informes: IAAPS (Noviembre 2026)')],
        )

    def test_sin_acceso_no_redirige_ni_anota(self):
        equipo = Group.objects.create(name='Equipo')
        self.con_enlace.grupos.add(equipo)

        respuesta = self.client.get(reverse('abrir_modulo', args=[self.con_enlace.id]))

        self.assertEqual(respuesta.status_code, 404)
        self.assertFalse(Acceso.objects.exists())

    def test_un_modulo_sin_enlace_no_se_abre(self):
        respuesta = self.client.get(reverse('abrir_modulo', args=[self.con_reportes.id]))

        self.assertEqual(respuesta.status_code, 404)

    def test_sin_sesion_pide_ingresar(self):
        self.client.logout()

        respuesta = self.client.get(reverse('abrir_modulo', args=[self.con_enlace.id]))

        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('login'), respuesta['Location'])
        self.assertFalse(Acceso.objects.exists())

    def test_el_registro_sobrevive_si_se_borra_la_cuenta(self):
        otro = get_user_model().objects.create_user('temporal')
        Acceso.anotar(otro, Acceso.ABRIR, self.con_enlace, 'Tablero')

        otro.delete()

        acceso = Acceso.objects.get()
        self.assertIsNone(acceso.usuario)
        self.assertEqual(acceso.nombre_usuario, 'temporal')

    def test_en_el_panel_solo_se_consulta(self):
        admin = get_user_model().objects.create_superuser('jefe')
        Acceso.anotar(self.usuario, Acceso.ABRIR, self.con_enlace, 'Tablero')
        self.client.force_login(admin)

        self.assertEqual(self.client.get('/admin/repositorio/acceso/').status_code, 200)
        self.assertEqual(self.client.get('/admin/repositorio/acceso/add/').status_code, 403)

    def test_borra_solo_los_registros_antiguos(self):
        antiguo = Acceso.anotar(self.usuario, Acceso.ABRIR, self.con_enlace, 'Tablero')
        Acceso.objects.filter(id=antiguo.id).update(fecha=timezone.now() - timedelta(days=400))
        Acceso.anotar(self.usuario, Acceso.ABRIR, self.con_enlace, 'Tablero')

        call_command('borrar_accesos_antiguos', dias=365, stdout=StringIO())

        self.assertEqual(Acceso.objects.count(), 1)
        self.assertFalse(Acceso.objects.filter(id=antiguo.id).exists())

    def test_no_borra_con_un_plazo_muy_corto(self):
        with self.assertRaises(CommandError):
            call_command('borrar_accesos_antiguos', dias=1, stdout=StringIO())


class CargarDemoTests(TestCase):
    def setUp(self):
        self.directorio_temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.directorio_temporal.cleanup)
        self.override_media = override_settings(MEDIA_ROOT=Path(self.directorio_temporal.name))
        self.override_media.enable()
        self.addCleanup(self.override_media.disable)

    def cargar(self, **opciones):
        call_command('cargar_demo', stdout=StringIO(), **opciones)

    def test_no_corre_fuera_de_desarrollo(self):
        with self.assertRaises(CommandError):
            self.cargar()
        self.assertFalse(Modulo.objects.filter(nombre='COMGES').exists())

    @override_settings(DEBUG=True)
    def test_carga_la_demo_sin_duplicar(self):
        self.cargar()
        self.cargar()

        self.assertEqual(Modulo.objects.filter(nombre='COMGES').count(), 1)
        self.assertEqual(Categoria.objects.filter(nombre='Territorio').count(), 1)
        self.assertEqual(Reporte.objects.count(), 2)
        self.assertTrue(Reporte.objects.get(titulo='Manual Series REM 2026 - Serie A').enlace.startswith('https://repositoriodeis.minsal.cl/'))
        per_capita = Modulo.objects.get(nombre='Per Cápita Comunal')
        self.assertTrue(per_capita.grupos.filter(name='Equipo Per Cápita').exists())
        self.assertEqual(Modulo.objects.get(nombre='Rendimientos y Agenda').enlace, '')

    @override_settings(DEBUG=True)
    def test_no_pisa_lo_que_ya_tiene_contenido(self):
        Modulo.objects.filter(nombre='Per Cápita Comunal').update(
            enlace='https://percapita.ejemplo.cl/', corte='Octubre 2026',
        )

        self.cargar(sin_usuarios=True)

        per_capita = Modulo.objects.get(nombre='Per Cápita Comunal')
        self.assertEqual(per_capita.enlace, 'https://percapita.ejemplo.cl/')
        self.assertEqual(per_capita.corte, 'Octubre 2026')

    @override_settings(DEBUG=True)
    def test_los_reportes_de_ejemplo_son_pdf_validos(self):
        self.cargar(sin_usuarios=True)

        self.assertEqual(Reporte.objects.exclude(archivo='').count(), 1)
        for reporte in Reporte.objects.exclude(archivo=''):
            with self.subTest(reporte=str(reporte)), reporte.archivo.open('rb') as archivo:
                validar_archivo_reporte(archivo)
                pdf = archivo.read()
                self.assertTrue(pdf.rstrip().endswith(b'%%EOF'))
                # Los lectores de PDF usan este índice: cada posición debe apuntar a su objeto.
                inicio_xref = int(re.search(rb'startxref\n(\d+)', pdf).group(1))
                self.assertEqual(pdf[inicio_xref:inicio_xref + 4], b'xref')
                posiciones = [int(p) for p in re.findall(rb'(\d{10}) 00000 n', pdf)]
                for numero, posicion in enumerate(posiciones, start=1):
                    self.assertTrue(pdf[posicion:].startswith(b'%d 0 obj' % numero))

    @override_settings(DEBUG=True)
    def test_crea_las_cuentas_de_ejemplo(self):
        self.cargar()

        equipo = get_user_model().objects.get(username='demo-equipo')
        general = get_user_model().objects.get(username='demo-general')
        self.assertTrue(equipo.groups.filter(name='Equipo Per Cápita').exists())
        self.assertFalse(general.groups.exists())
        self.assertFalse(equipo.is_staff or general.is_staff)


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


class CacheTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directorio_media = tempfile.TemporaryDirectory()
        cls.override_media = override_settings(MEDIA_ROOT=Path(cls.directorio_media.name))
        cls.override_media.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.override_media.disable()
        cls.directorio_media.cleanup()

    def test_las_paginas_con_sesion_no_se_guardan_en_el_navegador(self):
        usuario = get_user_model().objects.create_user('ana')
        modulo = Modulo.objects.create(nombre='Informes', enlace=ENLACE)
        reporte = Reporte.objects.create(
            modulo=modulo, titulo='IAAPS', anio=2026, mes=11, subido_por=usuario,
            archivo=SimpleUploadedFile('r.pdf', b'%PDF-1.4 prueba', content_type='application/pdf'),
        )
        self.client.force_login(usuario)

        for url in (
            reverse('inicio'),
            reverse('lista_reportes', args=[modulo.id]),
            reverse('abrir_modulo', args=[modulo.id]),
            reverse('descargar_reporte', args=[reporte.id]),
        ):
            with self.subTest(url=url):
                respuesta = self.client.get(url)
                self.assertIn('no-store', respuesta['Cache-Control'])
                self.assertIn('private', respuesta['Cache-Control'])
                respuesta.close()


class PoliticaDeContenidoTests(TestCase):
    def test_todas_las_paginas_llevan_la_politica(self):
        admin = get_user_model().objects.create_superuser('jefe')
        paginas = [self.client.get(reverse('login'))]
        self.client.force_login(admin)
        paginas += [self.client.get(reverse('inicio')), self.client.get('/admin/')]

        for respuesta in paginas:
            with self.subTest(url=respuesta.request['PATH_INFO']):
                politica = respuesta['Content-Security-Policy']
                self.assertIn("script-src 'self'", politica)
                self.assertIn("style-src 'self'", politica)
                self.assertIn("frame-ancestors 'none'", politica)

    def test_las_plantillas_no_llevan_scripts_ni_estilos_en_la_pagina(self):
        # Con la CSP, un <script> sin src o un style="" no funcionarían.
        for plantilla in Path(settings.BASE_DIR, 'templates').rglob('*.html'):
            with self.subTest(plantilla=plantilla.name):
                texto = plantilla.read_text(encoding='utf-8')
                self.assertIsNone(re.search(r'<script(?![^>]*\ssrc=)[^>]*>', texto))
                self.assertNotIn('style="', texto)


class LimiteDeIntentosTests(TestCase):
    CLAVE = 'clave-de-prueba-9'

    @classmethod
    def setUpTestData(cls):
        cls.ana = get_user_model().objects.create_user('ana', password=cls.CLAVE)
        cls.beto = get_user_model().objects.create_user('beto', password=cls.CLAVE)
        cls.jefe = get_user_model().objects.create_superuser('jefe', password=cls.CLAVE)

    def ingresar(self, usuario, clave, ip='10.0.0.1', url=None, **extra):
        cliente = Client(REMOTE_ADDR=ip, **extra)
        respuesta = cliente.post(url or reverse('login'), {'username': usuario, 'password': clave})
        return respuesta, cliente

    def fallar(self, usuario, veces, **kwargs):
        for numero in range(veces):
            self.ingresar(usuario, f'mala-{numero}', **kwargs)

    def test_tras_cinco_fallas_ni_la_clave_correcta_entra(self):
        self.fallar('ana', 5)

        respuesta, cliente = self.ingresar('ana', self.CLAVE)

        self.assertContains(respuesta, 'demasiados intentos fallidos')
        self.assertEqual(cliente.get(reverse('inicio')).status_code, 302)

    def test_cuatro_fallas_todavia_dejan_entrar_y_se_borran(self):
        self.fallar('ana', 4)

        respuesta, _ = self.ingresar('ana', self.CLAVE)

        self.assertEqual(respuesta.status_code, 302)
        self.assertFalse(IntentoFallido.objects.filter(nombre_usuario='ana').exists())

    def test_otra_cuenta_de_la_misma_oficina_sigue_entrando(self):
        self.fallar('ana', 5)

        respuesta, _ = self.ingresar('beto', self.CLAVE)

        self.assertEqual(respuesta.status_code, 302)

    def test_la_misma_cuenta_desde_otro_equipo_sigue_entrando(self):
        self.fallar('ana', 5, ip='10.0.0.1')

        respuesta, _ = self.ingresar('ana', self.CLAVE, ip='10.0.0.2')

        self.assertEqual(respuesta.status_code, 302)

    def test_el_bloqueo_termina_a_los_15_minutos(self):
        self.fallar('ana', 5)
        IntentoFallido.objects.update(fecha=timezone.now() - timedelta(minutes=16))

        respuesta, _ = self.ingresar('ana', self.CLAVE)

        self.assertEqual(respuesta.status_code, 302)

    def test_mismo_mensaje_aunque_la_cuenta_no_exista(self):
        self.fallar('no-existe', 5)

        respuesta, _ = self.ingresar('no-existe', 'x')

        self.assertContains(respuesta, 'demasiados intentos fallidos')

    def test_no_distingue_mayusculas_en_el_nombre(self):
        self.fallar('ANA', 5)

        respuesta, _ = self.ingresar('ana', self.CLAVE)

        self.assertContains(respuesta, 'demasiados intentos fallidos')

    def test_el_panel_tiene_el_mismo_limite(self):
        self.fallar('jefe', 5, url='/admin/login/')

        respuesta, cliente = self.ingresar('jefe', self.CLAVE, url='/admin/login/')

        self.assertContains(respuesta, 'demasiados intentos fallidos')
        self.assertEqual(cliente.get('/admin/').status_code, 302)

    @override_settings(DEBUG=False)
    def test_en_el_servidor_cuenta_la_ip_que_informa_nginx(self):
        self.fallar('ana', 5, ip='127.0.0.1', HTTP_X_REAL_IP='200.1.1.1')

        bloqueado, _ = self.ingresar('ana', self.CLAVE, ip='127.0.0.1', HTTP_X_REAL_IP='200.1.1.1')
        otro_equipo, _ = self.ingresar('ana', self.CLAVE, ip='127.0.0.1', HTTP_X_REAL_IP='200.1.1.2')

        self.assertContains(bloqueado, 'demasiados intentos fallidos')
        self.assertEqual(otro_equipo.status_code, 302)

    @override_settings(DEBUG=True)
    def test_en_desarrollo_no_cree_en_el_encabezado(self):
        self.fallar('ana', 5, ip='10.0.0.1', HTTP_X_REAL_IP='200.1.1.1')

        respuesta, _ = self.ingresar('ana', self.CLAVE, ip='10.0.0.1', HTTP_X_REAL_IP='200.1.1.2')

        self.assertContains(respuesta, 'demasiados intentos fallidos')

    def test_en_el_panel_se_desbloquea_borrando_los_intentos(self):
        self.fallar('ana', 5)
        admin = Client()
        admin.force_login(self.jefe)

        self.assertContains(admin.get('/admin/repositorio/intentofallido/'), '5 intentos fallidos de ingreso')
        IntentoFallido.objects.filter(nombre_usuario='ana').delete()
        respuesta, _ = self.ingresar('ana', self.CLAVE)

        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(admin.get('/admin/repositorio/intentofallido/add/').status_code, 403)


class ReporteConEnlaceTests(TestCase):
    MANUAL = 'https://repositoriodeis.minsal.cl/ContenidoSitioWeb2020/REM/2026/SERIE/Manual.pdf'

    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user('ana')
        cls.modulo = Modulo.objects.create(nombre='Informes')
        cls.reporte = Reporte.objects.create(
            modulo=cls.modulo, titulo='Manual Series REM', anio=2026, mes=11,
            enlace=cls.MANUAL, subido_por=cls.usuario,
        )

    def setUp(self):
        self.client.force_login(self.usuario)

    def test_la_lista_ofrece_ver_y_descargar_el_manual(self):
        respuesta = self.client.get(reverse('lista_reportes', args=[self.modulo.id]))

        self.assertContains(
            respuesta,
            f'href="{reverse("ver_reporte", args=[self.reporte.id])}" target="_blank" rel="noopener noreferrer"',
        )
        self.assertContains(respuesta, f'href="{reverse("descargar_reporte", args=[self.reporte.id])}"')

    def test_ver_lleva_al_enlace_y_lo_anota(self):
        respuesta = self.client.get(reverse('ver_reporte', args=[self.reporte.id]))

        self.assertRedirects(respuesta, self.MANUAL, fetch_redirect_response=False)
        acceso = Acceso.objects.get()
        self.assertEqual((acceso.tipo, acceso.detalle), (Acceso.VER, 'Informes: Manual Series REM (Noviembre 2026)'))

    def test_descargar_trae_el_pdf_y_lo_entrega_como_descarga(self):
        with patch('repositorio.views.traer_pdf', return_value=b'%PDF-1.4 manual') as traer:
            respuesta = self.client.get(reverse('descargar_reporte', args=[self.reporte.id]))

        traer.assert_called_once_with(self.MANUAL)
        self.assertEqual(respuesta.content, b'%PDF-1.4 manual')
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        self.assertEqual(respuesta['Content-Disposition'], 'attachment; filename="manual-series-rem-11-2026.pdf"')
        self.assertIn('no-store', respuesta['Cache-Control'])
        self.assertEqual(Acceso.objects.get().tipo, Acceso.DESCARGA)

    def test_si_el_sitio_no_responde_abre_el_enlace(self):
        with patch('repositorio.views.traer_pdf', side_effect=OSError('sin conexión')):
            respuesta = self.client.get(reverse('descargar_reporte', args=[self.reporte.id]))

        self.assertRedirects(respuesta, self.MANUAL, fetch_redirect_response=False)
        self.assertEqual(Acceso.objects.get().tipo, Acceso.ABRIR)

    def test_un_enlace_que_no_es_pdf_solo_se_abre(self):
        pagina = Reporte.objects.create(
            modulo=self.modulo, titulo='Tablero', anio=2026, mes=10,
            enlace='https://app.powerbi.com/groups/me/reports/abc', subido_por=self.usuario,
        )

        respuesta = self.client.get(reverse('lista_reportes', args=[self.modulo.id]))

        self.assertContains(respuesta, f'href="{reverse("ver_reporte", args=[pagina.id])}" target="_blank"')
        self.assertNotContains(respuesta, f'href="{reverse("descargar_reporte", args=[pagina.id])}"')
        self.assertContains(respuesta, 'Abrir')

    def test_el_corte_de_la_portada_tambien_lo_cuenta(self):
        self.assertContains(self.client.get(reverse('inicio')), '<li>Informes: Noviembre 2026</li>')

    def test_pide_archivo_o_enlace_pero_no_ambos(self):
        datos = {'modulo': self.modulo, 'titulo': 'Otro', 'anio': 2026, 'mes': 10, 'subido_por': self.usuario}
        sin_nada = Reporte(**datos)
        con_ambos = Reporte(**datos, enlace=self.MANUAL, archivo=SimpleUploadedFile('r.pdf', b'%PDF-1.4 x'))

        for reporte in (sin_nada, con_ambos):
            with self.subTest(archivo=bool(reporte.archivo)), self.assertRaises(ValidationError):
                reporte.full_clean()

    def test_el_enlace_debe_ser_https(self):
        reporte = Reporte(
            modulo=self.modulo, titulo='Inseguro', anio=2026, mes=10,
            enlace='http://repositoriodeis.minsal.cl/x.pdf', subido_por=self.usuario,
        )
        with self.assertRaises(ValidationError):
            reporte.full_clean()


class VerReporteTests(TestCase):
    @classmethod
    def setUpClass(cls):
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
        cls.usuario = get_user_model().objects.create_user('ana')
        cls.modulo = Modulo.objects.create(nombre='Informes')
        cls.pdf = Reporte.objects.create(
            modulo=cls.modulo, titulo='IAAPS', anio=2026, mes=11, subido_por=cls.usuario,
            archivo=SimpleUploadedFile('r.pdf', b'%PDF-1.4 prueba', content_type='application/pdf'),
        )
        cls.excel = Reporte.objects.create(
            modulo=cls.modulo, titulo='REM', anio=2026, mes=11, subido_por=cls.usuario,
            archivo=SimpleUploadedFile('r.xlsx', b'PK excel', content_type='application/octet-stream'),
        )

    def setUp(self):
        self.client.force_login(self.usuario)

    def test_el_pdf_se_muestra_en_el_navegador(self):
        respuesta = self.client.get(reverse('ver_reporte', args=[self.pdf.id]))

        try:
            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(respuesta['Content-Type'], 'application/pdf')
            self.assertTrue(respuesta['Content-Disposition'].startswith('inline'))
            self.assertIn('no-store', respuesta['Cache-Control'])
            self.assertEqual(respuesta['X-Content-Type-Options'], 'nosniff')
        finally:
            respuesta.close()

    def test_el_pdf_lleva_su_propia_politica_de_contenido(self):
        respuesta = self.client.get(reverse('ver_reporte', args=[self.pdf.id]))
        respuesta.close()

        politica = respuesta['Content-Security-Policy']
        self.assertIn("default-src 'none'", politica)
        self.assertIn("object-src 'self'", politica)
        self.assertIn("frame-ancestors 'none'", politica)

    def test_descargar_sigue_siendo_descarga(self):
        respuesta = self.client.get(reverse('descargar_reporte', args=[self.pdf.id]))
        respuesta.close()

        self.assertTrue(respuesta['Content-Disposition'].startswith('attachment'))

    def test_un_excel_no_se_muestra_se_descarga(self):
        respuesta = self.client.get(reverse('ver_reporte', args=[self.excel.id]))

        self.assertRedirects(respuesta, reverse('descargar_reporte', args=[self.excel.id]), fetch_redirect_response=False)

    def test_la_lista_ofrece_ver_y_descargar_el_pdf(self):
        respuesta = self.client.get(reverse('lista_reportes', args=[self.modulo.id]))

        self.assertContains(respuesta, f'href="{reverse("ver_reporte", args=[self.pdf.id])}" target="_blank"')
        self.assertContains(respuesta, f'href="{reverse("descargar_reporte", args=[self.pdf.id])}"')
        self.assertNotContains(respuesta, reverse('ver_reporte', args=[self.excel.id]))
        self.assertContains(respuesta, f'href="{reverse("descargar_reporte", args=[self.excel.id])}"')

    def test_ver_queda_en_el_registro(self):
        self.client.get(reverse('ver_reporte', args=[self.pdf.id])).close()

        acceso = Acceso.objects.get()
        self.assertEqual((acceso.tipo, acceso.detalle), (Acceso.VER, 'Informes: IAAPS (Noviembre 2026)'))

    def test_ver_respeta_los_grupos_y_la_sesion(self):
        self.modulo.grupos.add(Group.objects.create(name='Equipo'))
        self.assertEqual(self.client.get(reverse('ver_reporte', args=[self.pdf.id])).status_code, 404)

        self.client.logout()
        respuesta = self.client.get(reverse('ver_reporte', args=[self.pdf.id]))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('login'), respuesta['Location'])



class TraerPdfTests(TestCase):
    """Los resguardos de repositorio/remoto.py, sin conectarse a internet."""

    def direccion(self, ip):
        return patch('repositorio.remoto.socket.getaddrinfo', return_value=[(2, 1, 6, '', (ip, 443))])

    def test_solo_https(self):
        with self.assertRaises(EnlaceNoPermitido):
            verificar_destino('http://repositoriodeis.minsal.cl/manual.pdf')

    def test_no_trae_de_la_red_interna_ni_de_este_servidor(self):
        for ip in ('127.0.0.1', '10.0.0.5', '192.168.1.10', '169.254.169.254', '::1'):
            with self.subTest(ip=ip), self.direccion(ip), self.assertRaises(EnlaceNoPermitido):
                verificar_destino('https://sitio.cl/manual.pdf')

    def test_acepta_una_direccion_publica(self):
        with self.direccion('200.1.2.3'):
            verificar_destino('https://sitio.cl/manual.pdf')

    def respuesta(self, contenido):
        falsa = MagicMock()
        falsa.__enter__.return_value.read.return_value = contenido
        return patch('repositorio.remoto.urllib.request.OpenerDirector.open', return_value=falsa)

    def test_trae_un_pdf(self):
        with self.direccion('200.1.2.3'), self.respuesta(b'%PDF-1.7 contenido'):
            self.assertEqual(traer_pdf('https://sitio.cl/manual.pdf'), b'%PDF-1.7 contenido')

    def test_rechaza_lo_que_no_es_pdf(self):
        with self.direccion('200.1.2.3'), self.respuesta(b'<html>error</html>'), self.assertRaises(EnlaceNoPermitido):
            traer_pdf('https://sitio.cl/manual.pdf')

    def test_rechaza_archivos_muy_grandes(self):
        grande = b'%PDF-' + b'0' * MAX_BYTES
        with self.direccion('200.1.2.3'), self.respuesta(grande), self.assertRaises(EnlaceNoPermitido):
            traer_pdf('https://sitio.cl/manual.pdf')

    def test_las_redirecciones_tambien_se_revisan(self):
        manejador = _SoloHttps()
        with self.assertRaises(EnlaceNoPermitido):
            manejador.redirect_request(None, None, 302, 'Found', {}, 'http://sitio.cl/otro.pdf')



class FuenteDelReporteTests(TestCase):
    ORIGINAL = 'https://repositoriodeis.minsal.cl/ContenidoSitioWeb2020/REM/2026/SERIE/Manual.pdf'

    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user('ana')
        cls.modulo = Modulo.objects.create(nombre='Informes')

    def crear(self, **kwargs):
        return Reporte.objects.create(
            modulo=self.modulo, anio=2026, mes=11, subido_por=self.usuario,
            enlace=self.ORIGINAL, **kwargs,
        )

    def lista(self):
        self.client.force_login(self.usuario)
        return self.client.get(reverse('lista_reportes', args=[self.modulo.id]))

    def test_la_tarjeta_muestra_la_fuente_con_su_enlace(self):
        self.crear(titulo='Manual', fuente='MINSAL (DEIS)', fuente_enlace=self.ORIGINAL)

        self.assertContains(
            self.lista(),
            f'Fuente: <a href="{self.ORIGINAL}" target="_blank" rel="noopener noreferrer">MINSAL (DEIS)',
        )

    def test_la_fuente_sin_enlace_es_solo_texto(self):
        self.crear(titulo='Manual', fuente='MINSAL (DEIS)')

        respuesta = self.lista()

        self.assertContains(respuesta, '<small class="fuente">Fuente: MINSAL (DEIS)</small>')

    def test_sin_fuente_no_aparece(self):
        self.crear(titulo='Manual')

        self.assertNotContains(self.lista(), 'Fuente:')

    def test_el_enlace_de_la_fuente_debe_ser_https(self):
        reporte = Reporte(
            modulo=self.modulo, titulo='Otro', anio=2026, mes=10, subido_por=self.usuario,
            enlace=self.ORIGINAL, fuente='MINSAL', fuente_enlace='http://minsal.cl/',
        )
        with self.assertRaises(ValidationError):
            reporte.full_clean()

    def test_un_nombre_con_html_se_muestra_como_texto(self):
        self.crear(titulo='Manual', fuente='<script>alert(1)</script>')

        self.assertNotContains(self.lista(), '<script>alert(1)</script>')
