from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.utils.text import slugify

from .models import Modulo, Reporte


@login_required
def inicio(request):
    """Portada de las herramientas, con el último corte de cada una."""
    modulos = list(Modulo.objects.filter(activo=True).prefetch_related('reportes'))

    for modulo in modulos:
        # Los reportes vienen del más reciente al más antiguo (Meta.ordering).
        reportes = modulo.reportes.all()
        modulo.tiene_reportes = bool(reportes)
        if reportes:
            # Con reportes cargados, el corte es el período del más reciente.
            modulo.corte = reportes[0].periodo

    return render(request, 'inicio.html', {
        'modulos': modulos,
        'con_corte': [
            modulo for modulo in modulos
            if modulo.enlace or modulo.corte
        ],
    })


@login_required
def lista_reportes(request, modulo_id):
    """Lista los archivos disponibles de un módulo."""
    modulo = get_object_or_404(Modulo, id=modulo_id, activo=True)

    return render(request, 'reportes/lista.html', {
        'modulo': modulo,
        'reportes': list(modulo.reportes.all()),
    })


@login_required
def descargar_reporte(request, reporte_id):
    """Entrega un archivo privado solo a usuarios autenticados."""
    # Si el módulo se desactiva, sus archivos tampoco se pueden descargar.
    reporte = get_object_or_404(Reporte, id=reporte_id, modulo__activo=True)

    try:
        archivo = reporte.archivo.open('rb')
    except (FileNotFoundError, OSError):
        raise Http404('El archivo del reporte no está disponible.')

    extension = Path(reporte.archivo.name).suffix.lower()
    nombre_base = slugify(reporte.titulo) or 'reporte'
    nombre_descarga = f'{nombre_base}-{reporte.mes:02d}-{reporte.anio}{extension}'

    tipo_contenido = (
        'application/pdf' if extension == '.pdf'
        else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    return FileResponse(
        archivo,
        as_attachment=True,
        filename=nombre_descarga,
        content_type=tipo_contenido,
    )
