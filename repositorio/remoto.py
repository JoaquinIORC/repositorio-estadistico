"""Trae un PDF publicado en otro sitio, para entregarlo como descarga.

Los navegadores no dejan forzar la descarga de un archivo de otro sitio (lo
abren), así que para "Descargar" el portal lo trae y lo entrega él. El enlace
solo lo escribe un administrador, pero igual se limita qué se puede traer:
solo https (también en las redirecciones), solo direcciones públicas de
internet (nunca la red interna ni este mismo servidor), solo PDF y con tamaño
y tiempo máximos.
"""
import ipaddress
import socket
import urllib.error
import urllib.request
from urllib.parse import urlparse

MAX_BYTES = 25 * 1024 * 1024
ESPERA_SEGUNDOS = 15


class EnlaceNoPermitido(Exception):
    """El enlace no se puede traer: no es https, apunta a la red interna o no es un PDF."""


def verificar_destino(url):
    partes = urlparse(url)
    if partes.scheme != 'https' or not partes.hostname:
        raise EnlaceNoPermitido('Solo se traen enlaces https.')
    try:
        direcciones = {info[4][0] for info in socket.getaddrinfo(partes.hostname, partes.port or 443)}
    except socket.gaierror as error:
        raise EnlaceNoPermitido(f'No se encontró el sitio: {error}') from error
    for direccion in direcciones:
        if not ipaddress.ip_address(direccion.split('%')[0]).is_global:
            raise EnlaceNoPermitido('El enlace apunta a una dirección interna.')


class _SoloHttps(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        verificar_destino(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def traer_pdf(url):
    """Devuelve los bytes del PDF. Lanza EnlaceNoPermitido u OSError si no se puede."""
    verificar_destino(url)
    abridor = urllib.request.build_opener(_SoloHttps)
    pedido = urllib.request.Request(url, headers={'User-Agent': 'RepositorioEstadistico/1.0'})
    with abridor.open(pedido, timeout=ESPERA_SEGUNDOS) as respuesta:
        datos = respuesta.read(MAX_BYTES + 1)
    if len(datos) > MAX_BYTES:
        raise EnlaceNoPermitido('El archivo supera los 25 MB.')
    if not datos.startswith(b'%PDF-'):
        raise EnlaceNoPermitido('El enlace no entrega un PDF.')
    return datos
