from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from .models import Acceso, Categoria, Modulo, Reporte


def modulos_visibles(usuario):
    """Módulos activos que el usuario puede ver, según sus grupos."""
    return Modulo.objects.filter(activo=True).visibles_para(usuario)


@login_required
def inicio(request):
    """Portada de las herramientas, con el último corte de cada una."""
    modulos = list(
        modulos_visibles(request.user)
        .select_related('categoria')
        .prefetch_related('reportes')
    )

    for modulo in modulos:
        # Los reportes vienen del más reciente al más antiguo (Meta.ordering).
        reportes = modulo.reportes.all()
        modulo.tiene_reportes = bool(reportes)
        if reportes:
            # Con reportes cargados, el corte es el período del más reciente.
            modulo.corte = reportes[0].periodo

    # Una sección por categoría con módulos, en su orden; los sin categoría van al final.
    secciones = [
        {'categoria': categoria, 'modulos': [m for m in modulos if m.categoria_id == categoria.id]}
        for categoria in Categoria.objects.all()
    ]
    secciones.append({'categoria': None, 'modulos': [m for m in modulos if m.categoria_id is None]})

    return render(request, 'inicio.html', {
        'modulos': modulos,
        'secciones': [seccion for seccion in secciones if seccion['modulos']],
        'hay_categorias': any(m.categoria_id for m in modulos),
        'con_corte': [
            modulo for modulo in modulos
            if modulo.enlace or modulo.corte
        ],
    })


@login_required
def abrir_modulo(request, modulo_id):
    """Anota el acceso y lleva al enlace externo del módulo."""
    # Mismas reglas que la portada: sin acceso o sin enlace, 404.
    modulo = get_object_or_404(
        modulos_visibles(request.user).exclude(enlace=''), id=modulo_id,
    )
    Acceso.anotar(request.user, Acceso.ABRIR, modulo, modulo.nombre)
    # El enlace solo se guarda desde el panel y se valida como https.
    return redirect(modulo.enlace)


@login_required
def lista_reportes(request, modulo_id):
    """Lista los archivos disponibles de un módulo."""
    # 404 también si no tiene acceso: no confirma que el módulo existe.
    modulo = get_object_or_404(modulos_visibles(request.user), id=modulo_id)
    Acceso.anotar(request.user, Acceso.REPORTES, modulo, modulo.nombre)

    return render(request, 'reportes/lista.html', {
        'modulo': modulo,
        'reportes': list(modulo.reportes.all()),
    })


@login_required
def descargar_reporte(request, reporte_id):
    """Entrega un archivo privado solo a usuarios autenticados."""
    # Solo de módulos activos que el usuario puede ver; si no, 404 como en la lista.
    reporte = get_object_or_404(
        Reporte, id=reporte_id, modulo__in=modulos_visibles(request.user),
    )

    try:
        archivo = reporte.archivo.open('rb')
    except (FileNotFoundError, OSError):
        raise Http404('El archivo del reporte no está disponible.')

    Acceso.anotar(
        request.user, Acceso.DESCARGA, reporte.modulo,
        f'{reporte.modulo.nombre}: {reporte.titulo} ({reporte.periodo})',
    )

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
