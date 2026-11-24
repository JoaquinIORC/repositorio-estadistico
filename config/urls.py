
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_not_required
from django.urls import path

from repositorio import views

admin.site.site_header = 'Repositorio Estadístico'
admin.site.site_title = 'Repositorio Estadístico'

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path(
        'ingresar/',
        auth_views.LoginView.as_view(redirect_authenticated_user=True),
        name='login',
    ),
    path(
        'salir/',
        login_not_required(auth_views.LogoutView.as_view()),
        name='logout',
    ),
    path(
        'modulos/<int:modulo_id>/',
        views.lista_reportes,
        name='lista_reportes',
    ),
    path(
        'reportes/<int:reporte_id>/descargar/',
        views.descargar_reporte,
        name='descargar_reporte',
    ),
    path('admin/', admin.site.urls),
]
