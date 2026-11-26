from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.views.decorators.cache import never_cache

from .models import Acceso, Categoria, Modulo, Reporte
from .remoto import EnlaceNoPermitido, traer_pdf
from .seguridad import POLITICA_PDF


# Todas las páginas con sesión llevan never_cache: Cache-Control no-store, para que el
# navegador no guarde la portada ni los reportes después de cerrar sesión.


def modulos_visibles(usuario):
    """Módulos activos que el usuario puede ver, según sus grupos."""
    return Modulo.objects.filter(activo=True).visibles_para(usuario)


@never_cache
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


@never_cache
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


@never_cache
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


@never_cache
@login_required
def descargar_reporte(request, reporte_id):
    """Entrega el archivo para guardarlo en el computador."""
    return entregar_reporte(request, reporte_id, en_navegador=False)


@never_cache
@login_required
def ver_reporte(request, reporte_id):
    """Muestra el PDF en el navegador; desde ahí también se puede descargar."""
    return entregar_reporte(request, reporte_id, en_navegador=True)


def entregar_reporte(request, reporte_id, en_navegador):
    """Archivo privado: solo con sesión y de módulos activos que el usuario puede ver."""
    reporte = get_object_or_404(
        Reporte, id=reporte_id, modulo__in=modulos_visibles(request.user),
    )
    detalle = f'{reporte.modulo.nombre}: {reporte.titulo} ({reporte.periodo})'

    if reporte.enlace:
        if not en_navegador and reporte.es_pdf:
            return descargar_enlace(request, reporte, detalle)
        # Ver un documento publicado en otro sitio: se anota y se lleva al enlace (validado como https).
        Acceso.anotar(request.user, Acceso.VER if reporte.es_pdf else Acceso.ABRIR, reporte.modulo, detalle)
        return redirect(reporte.enlace)

    if en_navegador and not reporte.es_pdf:
        # Un Excel no se puede mostrar en el navegador: se descarga.
        return redirect('descargar_reporte', reporte_id=reporte.id)

    try:
        archivo = reporte.archivo.open('rb')
    except (FileNotFoundError, OSError):
        raise Http404('El archivo del reporte no está disponible.')

    Acceso.anotar(request.user, Acceso.VER if en_navegador else Acceso.DESCARGA, reporte.modulo, detalle)

    extension = Path(reporte.archivo.name).suffix.lower()
    nombre_base = slugify(reporte.titulo) or 'reporte'
    nombre_descarga = f'{nombre_base}-{reporte.mes:02d}-{reporte.anio}{extension}'

    tipo_contenido = (
        'application/pdf' if extension == '.pdf'
        else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    respuesta = FileResponse(
        archivo,
        as_attachment=not en_navegador,
        filename=nombre_descarga,
        content_type=tipo_contenido,
    )
    if en_navegador:
        # El visor de PDF del navegador no abre con la política general (object-src 'none'):
        # esta respuesta lleva una propia, que solo deja mostrar el PDF y nada más.
        respuesta.headers['Content-Security-Policy'] = POLITICA_PDF
    return respuesta


def descargar_enlace(request, reporte, detalle):
    """Trae el PDF enlazado y lo entrega como descarga; si no se puede, abre el enlace."""
    try:
        datos = traer_pdf(reporte.enlace)
    except (EnlaceNoPermitido, OSError):
        # El sitio no responde o no entrega un PDF: que al menos se pueda abrir allá.
        Acceso.anotar(request.user, Acceso.ABRIR, reporte.modulo, detalle)
        return redirect(reporte.enlace)

    Acceso.anotar(request.user, Acceso.DESCARGA, reporte.modulo, detalle)
    nombre = f'{slugify(reporte.titulo) or "reporte"}-{reporte.mes:02d}-{reporte.anio}.pdf'
    respuesta = HttpResponse(datos, content_type='application/pdf')
    respuesta['Content-Disposition'] = f'attachment; filename="{nombre}"'
    return respuesta
