from django.shortcuts import render

from .models import Modulo


def inicio(request):
    """Portada de las herramientas, con el último corte de cada una."""
    modulos = list(Modulo.objects.filter(activo=True))
    return render(request, 'inicio.html', {
        'modulos': modulos,
        'con_corte': [modulo for modulo in modulos if modulo.enlace or modulo.corte],
    })
