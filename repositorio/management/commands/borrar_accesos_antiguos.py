"""Borra los registros de accesos más antiguos que el plazo indicado.

Uso: python manage.py borrar_accesos_antiguos --dias 365
"""
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from repositorio.models import Acceso


class Command(BaseCommand):
    help = 'Borra los registros de accesos con más días de antigüedad que --dias (365 por defecto).'

    def add_arguments(self, parser):
        parser.add_argument('--dias', type=int, default=365)

    def handle(self, *args, dias, **opciones):
        if dias < 30:
            raise CommandError('Use 30 días o más, para no borrar registros recientes por error.')
        limite = timezone.now() - timedelta(days=dias)
        borrados, _ = Acceso.objects.filter(fecha__lt=limite).delete()
        self.stdout.write(f'Se borraron {borrados} registros anteriores al {limite:%d-%m-%Y}.')
