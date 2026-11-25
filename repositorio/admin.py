
from django.contrib import admin

from .models import Modulo, Reporte


@admin.register(Modulo)
class ModuloAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'corte', 'orden', 'activo')
    # El corte cambia cada semana o mes: se actualiza desde la lista.
    list_editable = ('corte', 'orden', 'activo')


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
