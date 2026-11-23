from django.db import migrations

MODULOS = (
    ('Per Cápita Comunal', 'Control y visualización de las inscripciones por centro.', 10),
    ('Rendimientos y Agenda', 'Oferta y demanda, y tasas de inasistencia por CESFAM y CECOSF.', 20),
    ('Indicadores IAAPS y REM', 'Reportes mensuales de indicadores.', 30),
)


def crear_modulos(apps, schema_editor):
    Modulo = apps.get_model('repositorio', 'Modulo')
    Modulo.objects.bulk_create(
        Modulo(nombre=nombre, descripcion=descripcion, orden=orden)
        for nombre, descripcion, orden in MODULOS
    )


class Migration(migrations.Migration):

    dependencies = [
        ('repositorio', '0001_initial'),
    ]

    operations = [
        # Al revertir no se borran: pueden tener enlaces y cortes ya cargados.
        migrations.RunPython(crear_modulos, migrations.RunPython.noop),
    ]
