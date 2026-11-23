from django.contrib import admin

from .models import Modulo


@admin.register(Modulo)
class ModuloAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'corte', 'orden', 'activo')
    # El corte cambia cada semana o mes: se actualiza desde la lista.
    list_editable = ('corte', 'orden', 'activo')
