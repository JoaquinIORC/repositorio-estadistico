"""Política de contenido (Content-Security-Policy) para todas las páginas.

Le dice al navegador que solo ejecute scripts y estilos servidos por el propio
portal. Si alguna vez se colara HTML malicioso en un nombre o una descripción,
el navegador no lo ejecutaría. Por eso las plantillas no llevan <script> ni
style="" escritos en la página: van en static/.

Django 5.2 no trae CSP propia; cuando se actualice a Django 6 se puede pasar a
su configuración SECURE_CSP.
"""

POLITICA = '; '.join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self'",
    "img-src 'self' data:",
    "font-src 'self'",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])


class PoliticaDeContenidoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        respuesta = self.get_response(request)
        respuesta.headers.setdefault('Content-Security-Policy', POLITICA)
        return respuesta
