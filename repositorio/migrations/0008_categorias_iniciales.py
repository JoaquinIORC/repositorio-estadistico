from django.db import migrations

CATEGORIAS = (
    ('Registros y gestión', 'Indicadores oficiales, población inscrita y seguimiento de metas.', 'azul', 10),
    ('Atención de salud', 'Actividad, agenda y rendimiento de los centros.', 'verde', 20),
)

# Módulo: (categoría, ícono). Solo se asignan si el módulo existe y no tiene categoría.
MODULOS = {
    'Per Cápita Comunal': ('Registros y gestión', 'personas'),
    'Indicadores IAAPS y REM': ('Registros y gestión', 'grafico'),
    'Rendimientos y Agenda': ('Atención de salud', 'escritorio'),
}


def crear_categorias(apps, schema_editor):
    Categoria = apps.get_model('repositorio', 'Categoria')
    Modulo = apps.get_model('repositorio', 'Modulo')

    categorias = {}
    for nombre, descripcion, color, orden in CATEGORIAS:
        categorias[nombre], _ = Categoria.objects.get_or_create(
            nombre=nombre,
            defaults={'descripcion': descripcion, 'color': color, 'orden': orden},
        )

    for nombre, (categoria, icono) in MODULOS.items():
        Modulo.objects.filter(nombre=nombre, categoria__isnull=True).update(
            categoria=categorias[categoria], icono=icono,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('repositorio', '0007_categorias'),
    ]

    operations = [
        # Al revertir no se borran: pueden haberse editado desde el panel.
        migrations.RunPython(crear_categorias, migrations.RunPython.noop),
    ]
