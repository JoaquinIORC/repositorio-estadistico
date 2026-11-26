# Repositorio Estadístico

Página con acceso restringido que reúne las herramientas estadísticas de la comuna y muestra el último corte de cada una. Es independiente del sistema de percapitados: tiene sus propias cuentas y su propia base, y no se conecta a los datos de personas.

## Uso diario

Todo se hace en **Administrar**, con una cuenta de administrador:

- **Agregar una herramienta:** Módulos, "Añadir módulo", con nombre, descripción, categoría, ícono, enlace `https` y último corte. Marcar "Nuevo" muestra esa etiqueta en la tarjeta.
- **Agrupar en secciones:** Categorías, "Añadir categoría", con nombre, descripción, color y orden. La portada muestra una sección por categoría con módulos activos; los módulos sin categoría van al final, en "Otras herramientas". El buscador de la portada filtra por nombre, descripción y categoría.
- **Actualizar un corte:** se edita directo en la lista de módulos.
- **Publicar un reporte mensual (IAAPS, REM u otro):** Reportes, "Añadir reporte", con módulo, título, año, mes y el archivo PDF o XLSX (hasta 10 MB). En la portada, un módulo sin enlace y con reportes muestra "Ver reportes", y su corte pasa a ser el período del reporte más reciente (por ejemplo, Noviembre 2026). En la lista, todo PDF tiene "Ver", que lo abre en el navegador en otra pestaña, y "Descargar"; un Excel solo "Descargar", y un enlace que no es PDF (por ejemplo, un Power BI) solo "Abrir". Los archivos solo se ven o descargan con sesión. Si el reporte es un enlace a un PDF de otro sitio, "Descargar" hace que el servidor lo traiga (solo https, solo PDF, hasta 25 MB, nunca desde la red interna) y lo entregue como descarga: el servidor necesita salida a internet. Si no lo logra, abre el enlace en su sitio. Hoy pasa con `repositoriodeis.minsal.cl`, que no envía completa la cadena de su certificado: los navegadores la completan solos, pero el servidor no, y no se desactiva la validación. No subir archivos con RUT, nombres ni otros datos de personas.
- **Dar acceso a una persona:** Usuarios, "Añadir usuario". Con una cuenta común solo ve la portada; no marcar "Es staff" salvo que deba administrar.
- **Restringir un módulo a un equipo:** crear el grupo en Grupos (solo el nombre; los permisos de la lista no hacen falta), agregar a las personas en su ficha de usuario, y elegir el grupo en "Grupos" del módulo. Un módulo sin grupos lo ven todos; con grupos, solo sus miembros y los superusuarios. La restricción vale también para sus reportes, aunque se tenga el enlace directo. La columna "Acceso" de la lista de módulos muestra quién ve cada uno.

**Registro de accesos:** en Administrar > Accesos registrados se ve quién abrió cada módulo, quién vio la lista de reportes y quién descargó cada reporte, y cuándo. Se filtra por tipo, módulo y fecha, y se busca por usuario. Nadie puede crear ni editar registros, y solo un superusuario los puede borrar. Para que la tabla no crezca sin límite, borrar los de más de un año:

```bash
.venv/bin/python manage.py borrar_accesos_antiguos --dias 365
```

Las tarjetas con enlace pasan por `/modulos/<id>/abrir/`, que anota el acceso y lleva al enlace. Lo que la persona haga después dentro de Per Cápita o Power BI queda en los registros de esas herramientas, no aquí.

Cada herramienta mantiene su propio control de acceso. Per Cápita pide su ingreso, y un Power BI debe estar compartido con cuentas institucionales: un enlace "Publicar en la web" (`view?r=`) lo puede abrir cualquiera que lo tenga.

**Cuenta bloqueada:** después de 5 claves incorrectas en 15 minutos, esa cuenta no puede entrar desde ese equipo durante 15 minutos, aunque luego escriba la clave correcta. Vale para el portal y para el panel. Otras cuentas, y la misma cuenta desde otro equipo, siguen entrando. Para desbloquear antes, un superusuario borra los registros de esa cuenta en Administrar > Intentos fallidos de ingreso; ahí también se ve si alguien está probando claves.

## Desarrollo

Requiere Python 3.10 o superior; con 3.9 o anterior, `pip` no encuentra Django 5.2 y la instalación falla. Ver la versión con `python --version`.

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
Copy-Item .env.example .env
```

Completar `DJANGO_SECRET_KEY` en `.env` con una clave nueva, que se genera con:

```powershell
.\.venv\Scripts\python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

Luego:

```powershell
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py createsuperuser
.\.venv\Scripts\python manage.py test
.\.venv\Scripts\python manage.py runserver 127.0.0.1:8002
```

Con `DJANGO_DEBUG=True` también se aceptan enlaces `http://localhost`, para conectar el percapitados local. En el servidor se exige siempre `https`.

Las páginas llevan una política de contenido (CSP, en `repositorio/seguridad.py`) que solo deja correr scripts y estilos de `static/`. Por eso, al editar plantillas, no escribir `<script>` con código ni `style="..."` dentro del HTML: ponerlos en `static/js/` o `static/css/portal.css`. Una prueba automática revisa que ninguna plantilla los tenga.

### Datos de ejemplo para una demostración

```powershell
.\.venv\Scripts\python manage.py cargar_demo
```

Carga las categorías y los módulos del ejemplo de Cristian, completa los tres módulos pedidos (Per Cápita restringido al grupo "Equipo Per Cápita", Rendimientos "En preparación" e IAAPS y REM con un reporte PDF de ejemplo y el manual de Series REM del DEIS como enlace) y crea dos cuentas comunes: `demo-equipo`, que ve Per Cápita, y `demo-general`, que no. Las claves se muestran al terminar y cambian cada vez que se corre. Los enlaces de ejemplo van a `example.org` y los reportes dicen que sus datos no son reales.

Se puede correr varias veces: no duplica nada ni cambia lo que ya tiene contenido. Solo funciona con `DJANGO_DEBUG=True`, así que no se puede cargar en el servidor. Para partir de cero, borrar `db.sqlite3` y la carpeta `media/`, y volver a correr `migrate`.

### Si la instalación falla

- **"Python was not found" o se abre la Microsoft Store:** Python no está instalado o no está en el PATH. Instalarlo desde python.org marcando "Add python.exe to PATH", y abrir una terminal nueva. Si ya está instalado sin el PATH, crear el entorno con su ruta completa, por ejemplo `& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m venv .venv`; después todo sigue con `.\.venv\Scripts\python`.
- **"No matching distribution found for Django==5.2.18":** la versión de Python es menor a 3.10. Instalar una más nueva y crear `.venv` de nuevo.
- **`ReadTimeoutError` al descargar paquetes:** la red cortó la descarga. Repetir con más tiempo de espera: `.\.venv\Scripts\pip install --timeout 120 -r requirements.txt`.
- **`KeyError: 'DJANGO_SECRET_KEY'`:** falta el archivo `.env`. Copiarlo desde `.env.example`.
- **"The SECRET_KEY setting must not be empty":** el `.env` existe, pero `DJANGO_SECRET_KEY` quedó vacía. Generar una clave con el comando de arriba y pegarla.

## Despliegue en el servidor de percapitados

Corre con su propio usuario de Linux, para que no pueda leer el `.env` de percapitados, y en el puerto 8002 (8000 y 8001 ya están en uso). Reemplazar `repositorio.ejemplo.cl` y `<url-del-repositorio>`.

```bash
sudo useradd --system --create-home --home-dir /srv/repositorio --shell /bin/bash repositorio
sudo chmod 755 /srv/repositorio
sudo -u repositorio -i
git clone <url-del-repositorio> repositorio-estadistico
cd repositorio-estadistico
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt gunicorn==26.2.0
cat > .env <<EOF
DJANGO_SECRET_KEY='$(.venv/bin/python -c "from django.core.management.utils import get_random_secret_key as k; print(k())")'
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=repositorio.ejemplo.cl
DJANGO_SESSION_MINUTOS=30
EOF
chmod 600 .env
.venv/bin/python manage.py check --deploy
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py createsuperuser
# La carpeta de inicio queda abierta (755) para que Nginx lea staticfiles/;
# la base y los reportes, no.
chmod 600 db.sqlite3
mkdir -p media && chmod 700 media
exit
```

```bash
sudo tee /etc/systemd/system/repositorio.service > /dev/null <<'EOF'
[Unit]
Description=Repositorio Estadistico (Gunicorn)
After=network.target

[Service]
User=repositorio
Group=repositorio
WorkingDirectory=/srv/repositorio/repositorio-estadistico
ExecStart=/srv/repositorio/repositorio-estadistico/.venv/bin/gunicorn config.wsgi:application --bind 127.0.0.1:8002 --workers 2
ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now repositorio
```

El certificado se obtiene igual que en la guía de despliegue de percapitados. La zona de `limit_req` debe tener un nombre propio, porque la de percapitados ya usa `ingreso`.

```bash
sudo tee /etc/nginx/sites-available/repositorio > /dev/null <<'EOF'
limit_req_zone $binary_remote_addr zone=ingreso_repositorio:10m rate=10r/m;

server {
    listen 80;
    server_name repositorio.ejemplo.cl;
    server_tokens off;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name repositorio.ejemplo.cl;
    server_tokens off;

    ssl_certificate     /etc/letsencrypt/live/repositorio.ejemplo.cl/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/repositorio.ejemplo.cl/privkey.pem;

    # Solo con el certificado definitivo funcionando.
    add_header Strict-Transport-Security "max-age=86400" always;

    # Los reportes pesan hasta 10 MB; Nginx rechaza más de 1 MB si no se indica.
    client_max_body_size 11m;

    # Sin location /media/: los reportes se entregan solo a través de Django, que exige sesión.

    location /static/ {
        alias /srv/repositorio/repositorio-estadistico/staticfiles/;
    }

    location = /ingresar/ {
        limit_req zone=ingreso_repositorio burst=10 nodelay;
        limit_req_status 429;
        proxy_pass http://127.0.0.1:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # El panel tiene su propio ingreso: mismo límite de intentos.
    location = /admin/login/ {
        limit_req zone=ingreso_repositorio burst=10 nodelay;
        limit_req_status 429;
        proxy_pass http://127.0.0.1:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://127.0.0.1:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
sudo ln -s /etc/nginx/sites-available/repositorio /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

`manage.py check --deploy` no debe mostrar avisos. Los de HSTS (W004) y redirección a HTTPS (W008) están silenciados en `config/settings.py` porque los resuelve esta configuración de Nginx.

### Actualizar a una versión nueva

```bash
sudo -u repositorio -i
cd repositorio-estadistico
git pull
.venv/bin/pip install -r requirements.txt gunicorn==26.2.0
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py check --deploy
exit
sudo systemctl restart repositorio
```

Antes de `migrate`, respaldar como se indica abajo: algunas versiones agregan tablas (categorías, grupos por módulo, registro de accesos).

### Respaldos

La base es el archivo `db.sqlite3` y los reportes subidos quedan en la carpeta `media/`: incluir ambos en los respaldos del servidor. Copiar `db.sqlite3` mientras el sistema funciona puede dejar una copia a medias; esto saca una copia consistente:

```bash
sudo -u repositorio -i
cd repositorio-estadistico
mkdir -p ~/respaldos && chmod 700 ~/respaldos
.venv/bin/python -c "import sqlite3; o = sqlite3.connect('db.sqlite3'); d = sqlite3.connect('/srv/repositorio/respaldos/db-$(date +%F).sqlite3'); o.backup(d); d.close()"
tar czf ~/respaldos/media-$(date +%F).tar.gz media
```

La carpeta `respaldos` queda solo para el usuario `repositorio`, igual que `db.sqlite3` y `media/`: los reportes y el registro de accesos no deben quedar a la vista de otras cuentas del servidor. Si el sistema ya estaba instalado antes de este cambio, aplicar los permisos una vez:

```bash
sudo -u repositorio -i
cd repositorio-estadistico
chmod 600 db.sqlite3
mkdir -p media && chmod -R go-rwx media
```
