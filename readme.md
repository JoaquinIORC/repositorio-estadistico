# Repositorio Estadístico

Página con acceso restringido que reúne las herramientas estadísticas de la comuna y muestra el último corte de cada una. Es independiente del sistema de percapitados: tiene sus propias cuentas y su propia base, y no se conecta a los datos de personas.

## Uso diario

Todo se hace en **Administrar**, con una cuenta de administrador:

- **Agregar una herramienta:** Módulos, "Añadir módulo", con nombre, descripción, categoría, ícono, enlace `https` y último corte. Marcar "Nuevo" muestra esa etiqueta en la tarjeta.
- **Agrupar en secciones:** Categorías, "Añadir categoría", con nombre, descripción, color y orden. La portada muestra una sección por categoría con módulos activos; los módulos sin categoría van al final, en "Otras herramientas". El buscador de la portada filtra por nombre, descripción y categoría.
- **Actualizar un corte:** se edita directo en la lista de módulos.
- **Publicar un reporte mensual (IAAPS, REM u otro):** Reportes, "Añadir reporte", con módulo, título, año, mes y el archivo PDF o XLSX (hasta 10 MB). En la portada, un módulo sin enlace y con reportes muestra "Ver reportes", y su corte pasa a ser el período del reporte más reciente (por ejemplo, Noviembre 2026). Los archivos solo se descargan con sesión. No subir archivos con RUT, nombres ni otros datos de personas.
- **Dar acceso a una persona:** Usuarios, "Añadir usuario". Con una cuenta común solo ve la portada; no marcar "Es staff" salvo que deba administrar.
- **Restringir un módulo a un equipo:** crear el grupo en Grupos (solo el nombre; los permisos de la lista no hacen falta), agregar a las personas en su ficha de usuario, y elegir el grupo en "Grupos" del módulo. Un módulo sin grupos lo ven todos; con grupos, solo sus miembros y los superusuarios. La restricción vale también para sus reportes, aunque se tenga el enlace directo. La columna "Acceso" de la lista de módulos muestra quién ve cada uno.

Cada herramienta mantiene su propio control de acceso. Per Cápita pide su ingreso, y un Power BI debe estar compartido con cuentas institucionales: un enlace "Publicar en la web" (`view?r=`) lo puede abrir cualquiera que lo tenga.

## Desarrollo

Requiere Python 3.10 o superior; con 3.9 o anterior, `pip` no encuentra Django 5.2 y la instalación falla. Ver la versión con `python --version`.

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
Copy-Item .env.example .env
```

Completar `DJANGO_SECRET_KEY` en `.env` y luego:

```powershell
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py createsuperuser
.\.venv\Scripts\python manage.py test
.\.venv\Scripts\python manage.py runserver 127.0.0.1:8002
```

Con `DJANGO_DEBUG=True` también se aceptan enlaces `http://localhost`, para conectar el percapitados local. En el servidor se exige siempre `https`.

### Si la instalación falla

- **"Python was not found" o se abre la Microsoft Store:** Python no está instalado o no está en el PATH. Instalarlo desde python.org marcando "Add python.exe to PATH", y abrir una terminal nueva.
- **"No matching distribution found for Django==5.2.18":** la versión de Python es menor a 3.10. Instalar una más nueva y crear `.venv` de nuevo.
- **`ReadTimeoutError` al descargar paquetes:** la red cortó la descarga. Repetir con más tiempo de espera: `.\.venv\Scripts\pip install --timeout 120 -r requirements.txt`.
- **`KeyError: 'DJANGO_SECRET_KEY'`:** falta el archivo `.env` o la clave está vacía.

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

La base es el archivo `db.sqlite3` y los reportes subidos quedan en la carpeta `media/`: incluir ambos en los respaldos del servidor.
