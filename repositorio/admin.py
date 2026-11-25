
from django.contrib import admin

from .models import Acceso, Categoria, Modulo, Reporte


@admin.register(Acceso)
class AccesoAdmin(admin.ModelAdmin):
    """Solo consulta: los registros los escribe el sistema y nadie los edita."""

    list_display = ('fecha', 'nombre_usuario', 'tipo', 'detalle')
    list_filter = ('tipo', 'modulo', 'fecha')
    search_fields = ('nombre_usuario', 'detalle')
    date_hierarchy = 'fecha'
    list_per_page = 100

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        # Borrar queda para un superusuario, por ejemplo al limpiar registros antiguos.
        return request.user.is_superuser


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'color', 'orden')
    list_editable = ('color', 'orden')


@admin.register(Modulo)
class ModuloAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'acceso', 'corte', 'orden', 'nuevo', 'activo')
    # El corte cambia cada semana o mes: se actualiza desde la lista.
    list_editable = ('categoria', 'corte', 'orden', 'nuevo', 'activo')
    list_filter = ('categoria', 'grupos', 'activo')
    search_fields = ('nombre', 'descripcion')
    filter_horizontal = ('grupos',)
    fields = (
        'nombre', 'descripcion', 'categoria', 'icono', 'enlace', 'corte',
        'grupos', 'orden', 'nuevo', 'activo',
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('grupos')

    @admin.display(description='acceso')
    def acceso(self, modulo):
        grupos = [grupo.name for grupo in modulo.grupos.all()]
        return ', '.join(grupos) if grupos else 'Todos'


@admin.register(Reporte)
class ReporteAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'modulo', 'anio', 'mes', 'subido_en', 'subido_por')
    list_filter = ('modulo', 'anio')
    search_fields = ('titulo', 'modulo__nombre')
    readonly_fields = ('subido_en', 'subido_por')
    ordering = ('-anio', '-mes', '-subido_en')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.subido_por = request.user
        super().save_model(request, obj, form, change)
