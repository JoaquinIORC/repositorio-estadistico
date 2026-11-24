from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Modulo

ENLACE = 'https://app.powerbi.com/groups/me/reports/abc'


class AccesoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user('ana', password='clave-de-prueba-9')

    def test_sin_sesion_lleva_al_ingreso(self):
        respuesta = self.client.get(reverse('inicio'))

        self.assertRedirects(respuesta, f'{reverse("login")}?next=/')

    def test_con_clave_correcta_entra(self):
        respuesta = self.client.post(
            reverse('login'), {'username': 'ana', 'password': 'clave-de-prueba-9'}, follow=True,
        )

        self.assertContains(respuesta, 'Información disponible')

    def test_con_clave_incorrecta_no_entra(self):
        self.client.post(reverse('login'), {'username': 'ana', 'password': 'otra'})

        self.assertEqual(self.client.get(reverse('inicio')).status_code, 302)

    def test_con_clave_incorrecta_anuncia_el_error(self):
        respuesta = self.client.post(reverse('login'), {'username': 'ana', 'password': 'otra'})

        self.assertContains(respuesta, 'role="alert"')

    def test_el_ingreso_no_muestra_la_barra_superior(self):
        self.assertNotContains(self.client.get(reverse('login')), 'class="barra"')

    def test_un_usuario_comun_no_administra(self):
        self.client.force_login(self.usuario)

        self.assertNotContains(self.client.get(reverse('inicio')), 'Administrar')
        self.assertEqual(self.client.get('/admin/repositorio/modulo/').status_code, 302)

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

        for nombre in ('Per Cápita Comunal', 'Rendimientos y Agenda', 'Indicadores IAAPS y REM'):
            self.assertContains(respuesta, nombre)
        self.assertContains(respuesta, 'En preparación', count=3)
        self.assertContains(respuesta, 'todavía no hay cortes informados')

    def test_un_modulo_nuevo_aparece_con_su_enlace_y_corte(self):
        Modulo.objects.create(nombre='Tablero nuevo', enlace=ENLACE, corte='Semana 47')

        respuesta = self.abrir()

        self.assertContains(respuesta, 'Tablero nuevo: Semana 47')
        self.assertContains(respuesta, f'href="{ENLACE}" target="_blank" rel="noopener noreferrer"')

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
        Modulo.objects.create(nombre='Tablero oculto', enlace=ENLACE, activo=False)

        self.assertNotContains(self.abrir(), 'Tablero oculto')

    def test_el_enlace_debe_ser_https(self):
        for enlace in ('http://app.powerbi.com/x', 'javascript:alert(1)'):
            with self.subTest(enlace=enlace), self.assertRaises(ValidationError):
                Modulo(nombre='Inseguro', enlace=enlace).full_clean()

    @override_settings(DEBUG=True)
    def test_en_desarrollo_acepta_http_solo_hacia_este_computador(self):
        Modulo(nombre='Local', enlace='http://localhost:8000/').full_clean()
        Modulo(nombre='Local', enlace='http://127.0.0.1:8000').full_clean()
        for enlace in ('http://localhost.malo.cl/', 'http://localhost@malo.cl/', 'http://malo.cl/'):
            with self.subTest(enlace=enlace), self.assertRaises(ValidationError):
                Modulo(nombre='Inseguro', enlace=enlace).full_clean()

    def test_fuera_de_desarrollo_no_acepta_localhost(self):
        with self.assertRaises(ValidationError):
            Modulo(nombre='Local', enlace='http://localhost:8000/').full_clean()
