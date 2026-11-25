# Matriz de pruebas

## Primera pasada: 24-11-2026

- **Versión probada:** `main` (`fb56096`) con el PR #1 de diseño (`2b7f3cb`).
- **Ejecutó:** Joaquín Orellana, en reemplazo de Simón Jofré.
- **Entorno:** Windows 11, Python 3.12, Django 5.2.18 y una base SQLite desechable, con módulos y usuarios de prueba. Navegador: Chromium.
- **Resultado:** 23 casos aprobados, 1 aprobado con observación y 5 pendientes. No hay fallas.

Evidencia:

- **Cliente:** el caso se ejecutó con el cliente de pruebas de Django contra el sistema funcionando, enviando los mismos formularios que el navegador.
- **Navegador:** el caso se ejecutó a mano en el navegador.
- **Revisión PR #1:** el caso se revisó junto con el PR de diseño, en 1280, 768 y 375 px.

### Instalación

| ID | Caso | Pasos | Esperado | Obtenido | Estado | Evidencia |
|---|---|---|---|---|---|---|
| I-01 | Instalación desde cero | Clonar de GitHub, crear el entorno, instalar `requirements.txt`, crear `.env`, `migrate` | El sistema queda listo para usarse | Funcionó con Python 3.15 en un entorno nuevo (23-11). Las dependencias sirven desde Python 3.10; con 3.9 o anterior la instalación falla. José reportó un error al instalar, sin el texto del error | Aprobado con observación | Navegador y consola |
| I-02 | Pruebas automáticas | `python manage.py test` | Terminan en `OK` | 16 pruebas en `OK` | Aprobado | Consola |

### Acceso

| ID | Caso | Pasos | Esperado | Obtenido | Estado | Evidencia |
|---|---|---|---|---|---|---|
| A-01 | Sin sesión | Abrir `/` sin haber ingresado | Lleva al ingreso | 302 hacia `/ingresar/?next=/` | Aprobado | Cliente |
| A-02 | Clave incorrecta | Ingresar con una clave errónea | No entra y muestra el error | Muestra el error en un aviso que lee el lector de pantalla y sigue sin sesión | Aprobado | Cliente y navegador |
| A-03 | Usuario común | Ingresar con una cuenta sin permisos de administración | Ve la portada, sin "Administrar", y no entra al panel | Portada 200, sin "Administrar". `/admin/` y `/admin/repositorio/modulo/` llevan al ingreso del panel | Aprobado | Cliente |
| A-04 | Botón Atrás tras cerrar sesión | Entrar, cerrar sesión y presionar Atrás | No muestra la portada | Vuelve a pedir el ingreso (`/ingresar/?next=/`) | Aprobado | Navegador |
| A-05 | Sesión vencida | Dejar vencer la sesión | Pide ingresar de nuevo | La sesión dura 30 minutos y se renueva en cada visita. Vencida, `/` lleva al ingreso. Se simuló adelantando el vencimiento en la base | Aprobado | Cliente |
| A-06 | Usuario desactivado | Desactivar la cuenta e intentar ingresar | No entra | Muestra el error de ingreso y sigue sin sesión | Aprobado | Cliente |
| A-07 | Percapitados y repositorio a la vez | Tener ambos sistemas abiertos en el mismo navegador | Ninguno cierra la sesión del otro | Usan cookies distintas (`sessionid_repositorio` y `csrftoken_repositorio`). Probado el 23-11 con ambos abiertos | Aprobado | Navegador |

### Módulos

| ID | Caso | Pasos | Esperado | Obtenido | Estado | Evidencia |
|---|---|---|---|---|---|---|
| M-01 | Crear un módulo | Administrar > Módulos > Añadir, con enlace `https` | Aparece en la portada | Se guarda y aparece | Aprobado | Cliente |
| M-02 | Módulo sin enlace | Ver un módulo sin enlace en la portada | "En preparación" y sin enlace | Muestra "En preparación" y no se puede abrir | Aprobado | Cliente y navegador |
| M-03 | Módulo con enlace | Ver un módulo con enlace | Abre en otra pestaña | `target="_blank"`, `rel="noopener noreferrer"` y aviso "se abre en otra pestaña" para el lector de pantalla | Aprobado | Cliente |
| M-04 | Desactivar | Quitar "Activo" y guardar | Deja de aparecer | Ya no aparece | Aprobado | Cliente |
| M-05 | Orden | Cambiar el orden a 1 | Pasa al primer lugar | Queda primero | Aprobado | Cliente |
| M-06 | Enlaces inseguros | Guardar `http://ejemplo.cl` y `javascript:alert(1)` | Los rechaza | "Use un enlace que comience con https://." e "Introduzca una URL válida." No se crea ningún módulo | Aprobado | Cliente |
| M-07 | Nombre repetido | Crear un módulo con un nombre existente | Lo rechaza | "Ya existe Módulo con este Nombre." | Aprobado | Cliente |

### Sello de trazabilidad

| ID | Caso | Pasos | Esperado | Obtenido | Estado | Evidencia |
|---|---|---|---|---|---|---|
| S-01 | Sin cortes | Portada sin enlaces ni cortes | "todavía no hay cortes informados" | Lo muestra | Aprobado | Cliente |
| S-02 | Enlace sin corte | Módulo con enlace y corte vacío | "sin informar" | "Prueba QA: sin informar" | Aprobado | Cliente |
| S-03 | Varios cortes | Tres módulos con corte | Los tres, separados | Los tres, en una línea separada por barras en escritorio y en lista en celular | Aprobado | Cliente y revisión PR #1 |
| S-04 | Editar el corte desde la lista | Cambiar el corte en la lista de módulos y guardar | Se ve al recargar | "Semana 47" pasó a "Semana 48" en la portada | Aprobado | Navegador |

### Power BI

| ID | Caso | Pasos | Esperado | Obtenido | Estado | Evidencia |
|---|---|---|---|---|---|---|
| P-01 | Enlace protegido | Abrir el enlace de Rendimientos en una ventana privada, sin sesión de Microsoft | Pide ingreso | Falta el enlace de Power BI | Pendiente | |

### Diseño (PR #1)

| ID | Caso | Pasos | Esperado | Obtenido | Estado | Evidencia |
|---|---|---|---|---|---|---|
| D-01 | Tamaños de pantalla | Ver la portada en 1280, 768 y 375 px | Sin scroll horizontal ni textos cortados | 4, 2 y 1 columnas. Un nombre de 80 caracteres y una descripción de 200 no se salen | Aprobado | Revisión PR #1 |
| D-02 | Teclado | Recorrer con Tab | Orden lógico y foco visible | Saltar al contenido, marca, Administrar, Cerrar sesión y tarjetas. Contorno de 3 px | Aprobado | Revisión PR #1 |
| D-03 | Contraste | Medir el texto de la portada | 4,5:1 o más | El menor es 5,1:1, en la descripción de las tarjetas "En preparación" | Aprobado | Revisión PR #1 |
| D-04 | Mostrar contraseña | Usar "Mostrar" y "Ocultar" | Cambia la visibilidad de la clave | Funciona, y al enviar vuelve a ocultarla | Aprobado | Navegador |

### IAAPS y REM

| ID | Caso | Pasos | Esperado | Obtenido | Estado | Evidencia |
|---|---|---|---|---|---|---|
| R-01 | Documento correcto | Abrir cada enlace o reporte | Abre el documento que corresponde | Falta el trabajo de Daniel | Pendiente | |
| R-02 | Corte | Comparar el sello con el último mes disponible | Coinciden | Falta el trabajo de Daniel | Pendiente | |
| R-03 | Archivos sin sesión | Si hay archivos, pedirlos sin sesión | No se listan ni descargan | Falta el trabajo de Daniel | Pendiente | |
| R-04 | Archivos inválidos | Si hay archivos, subir uno de otro tipo, uno renombrado y uno de más de 10 MB | Los rechaza | Falta el trabajo de Daniel | Pendiente | |

### Observaciones que no bloquean

- **Ingreso sin nombre del sistema:** la pantalla de ingreso dice "Iniciar sesión", pero no "Repositorio Estadístico". Como percapitados también corre en el mismo computador, alguien puede confundir en qué sistema está entrando.
- **Aviso de Bloq Mayús:** mientras está vacío se oculta con `display: none`, y algunos lectores de pantalla no anuncian un aviso que estaba oculto al aparecer.
- **A-04 en otros navegadores:** se probó en Chromium. Conviene repetirlo en Chrome o Edge del computador de la demostración, porque algunos navegadores guardan la página anterior en memoria.

### Recomendación

Se puede mostrar a Cristian lo que ya está: ingreso, portada, Per Cápita, sello y administración de módulos. Rendimientos se muestra solo después de que P-01 esté aprobado.

## Segunda pasada: 25-11-2026

- **Versión probada:** `fix/centrar-secciones-portada` (`434dac2`): `main` (`78a35b2`) más el PR #9, que es como queda `main` al unirlo.
- **Ejecutó:** Joaquín Orellana, en reemplazo de Simón Jofré.
- **Entorno:** Windows 11, Python 3.12.0, Django 5.2.18, una copia recién clonada de GitHub con una base SQLite desechable, y Chromium (panel del navegador de la aplicación).
- **Resultado:** de 62 casos, 51 aprobados, 3 aprobados con observación y 8 pendientes. No hay fallas. Siguen pendientes R-01, R-02 y P-01.

Evidencia: igual que en la primera pasada. **Cliente** es el cliente de pruebas de Django contra la copia funcionando, con los mismos formularios del panel; **Navegador** es a mano en Chromium, con mediciones hechas en la misma página (tamaños, contraste, foco); **Consola** son los comandos de `manage.py`.

Cambios desde la primera pasada, en estas ramas:

- `feature/integrar-iaaps-rem`: reportes IAAPS y REM de Daniel, unidos con el diseño del PR #1.
- `feature/buscador-categorias`: secciones por categoría, buscador, íconos y etiqueta "Nuevo".
- `fix/observaciones-pruebas`: observaciones de la primera pasada.
- `feature/acceso-por-grupo`: módulos visibles solo para ciertos grupos de usuarios.
- `feature/demo-registro-produccion`: datos de ejemplo (`cargar_demo`), registro de accesos y ajustes para el servidor.
- `fix/centrar-secciones-portada` (PR #9): tarjetas cuadradas con el color de su categoría, secciones y sello centrados.

Se repitieron los casos de la primera pasada que dependen de la portada, más R-03 y R-04, que ya no requieren los reportes reales.

### Casos repetidos de la primera pasada

| ID | Caso | Obtenido | Estado | Evidencia |
|---|---|---|---|---|
| I-01 | Instalación desde cero | Ver O-04 | Aprobado con observación | Consola |
| I-02 | Pruebas automáticas | 59 pruebas en `OK` | Aprobado | Consola |
| A-01 | Sin sesión | 302 hacia `/ingresar/?next=/` | Aprobado | Cliente |
| A-02 | Clave incorrecta | Aviso con `role="alert"` y sigue sin sesión | Aprobado | Cliente |
| A-03 | Usuario común | Portada 200, sin "Administrar". `/admin/` y `/admin/repositorio/modulo/` responden 302 | Aprobado | Cliente |
| A-04 | Botón Atrás tras cerrar sesión | Vuelve a `/ingresar/?next=/` en Chromium (Chrome y Edge: ver O-03) | Aprobado | Navegador |
| A-05 | Sesión vencida | Sesión de 30 minutos; vencida (simulada en la base), `/` lleva al ingreso | Aprobado | Cliente |
| A-06 | Usuario desactivado | Muestra el error de ingreso y sigue sin sesión | Aprobado | Cliente |
| A-07 | Percapitados y repositorio a la vez | Cookies `sessionid_repositorio` y `csrftoken_repositorio`, sin cambios desde la primera pasada. No se repitió con percapitados abierto | Aprobado | Cliente |
| M-01 | Crear un módulo | Se guarda desde el panel y aparece en la portada | Aprobado | Cliente |
| M-02 | Módulo sin enlace | Tarjeta gris "En preparación", sin enlace | Aprobado | Cliente |
| M-03 | Módulo con enlace | Ahora apunta a `/modulos/<id>/abrir/` (registro de accesos), con `target="_blank"`, `rel="noopener noreferrer"` y el aviso para el lector de pantalla | Aprobado | Cliente |
| M-04 | Desactivar | Deja de aparecer | Aprobado | Cliente |
| M-05 | Orden | Con orden 1 queda primero dentro de su sección (con categorías, el orden es por sección) | Aprobado | Cliente |
| M-06 | Enlaces inseguros | "Use un enlace que comience con https://." e "Introduzca una URL válida."; no se crea ninguno | Aprobado | Cliente |
| M-07 | Nombre repetido | "Ya existe Módulo con este Nombre." | Aprobado | Cliente |
| S-01 | Sin cortes | Base nueva: "todavía no hay cortes informados" | Aprobado | Cliente |
| S-02 | Enlace sin corte | "Prueba QA: sin informar" | Aprobado | Cliente |
| S-03 | Varios cortes | Cada corte en su propio elemento; en celular, en lista | Aprobado | Cliente y navegador |
| S-04 | Editar el corte desde la lista | "Semana 47" pasó a "Semana 48" en la portada | Aprobado | Navegador |
| D-01 | Tamaños de pantalla | Ver D-05 y C-09 | Aprobado | Navegador |
| D-02 | Teclado | Saltar al contenido, marca, Administrar, Cerrar sesión, buscador y tarjetas, en ese orden. Contorno de 3 px en todos | Aprobado | Navegador |
| D-03 | Contraste | Textos de la portada: 5,39:1 o más. Tarjetas: ver D-07 | Aprobado | Navegador |
| D-04 | Mostrar contraseña | Cambia entre "Mostrar" y "Ocultar", y al enviar vuelve a ocultarla | Aprobado | Navegador |
| R-03 | Archivos sin sesión | Con reportes de prueba: la lista y la descarga llevan al ingreso, y la dirección no muestra el nombre del archivo | Aprobado | Cliente |
| R-04 | Archivos inválidos | Con reportes de prueba, desde el panel: rechaza un PDF renombrado, un `.txt` y uno de más de 10 MB | Aprobado | Cliente |
| R-01, R-02 | Documento y corte reales | Requieren los reportes reales de IAAPS y REM | Pendiente | |
| P-01 | Enlace protegido de Power BI | Falta el enlace | Pendiente | |

### Reportes (complementa R-01 a R-04)

| ID | Caso | Pasos | Esperado | Obtenido | Estado | Evidencia |
|---|---|---|---|---|---|---|
| R-05 | Corte desde los reportes | Subir reportes de octubre y noviembre al módulo IAAPS y REM | El sello dice "Indicadores IAAPS y REM: Noviembre 2026", aunque el corte escrito en el panel sea otro | Con el corte del panel en "Semana 40", se subieron desde el panel reportes de octubre y noviembre: el sello dice "Indicadores IAAPS y REM: Noviembre 2026" | Aprobado | Cliente |
| R-06 | Tarjeta "Ver reportes" | Dejar el módulo sin enlace y con un reporte | La tarjeta lleva a la lista de reportes y cada uno se descarga | "Ver reportes" lleva a la lista (200) y la descarga responde 200 con `iaaps-comunal-11-2026.pdf`. Página de reportes revisada también en tablet | Aprobado | Cliente y navegador |
| R-07 | Módulo desactivado | Desactivar el módulo y abrir el enlace de descarga de uno de sus reportes | No se descarga (página no encontrada) | Con el módulo desactivado, la descarga responde 404 | Aprobado | Cliente |
| R-08 | Archivo de 10 MB en el servidor | Subir un PDF de entre 1 y 10 MB en el servidor, con Nginx | Se guarda. Sin `client_max_body_size` Nginx lo rechaza con error 413 | Requiere el servidor con Nginx | Pendiente |  |

### Categorías y buscador

| ID | Caso | Pasos | Esperado | Obtenido | Estado | Evidencia |
|---|---|---|---|---|---|---|
| C-01 | Categorías iniciales | Migrar una base nueva | Per Cápita e IAAPS y REM en "Registros y gestión"; Rendimientos en "Atención de salud" | En una base recién migrada: Per Cápita e IAAPS y REM en "Registros y gestión"; Rendimientos en "Atención de salud" | Aprobado | Cliente |
| C-02 | Crear una categoría | Administrar > Categorías > Añadir, y asignarle un módulo | Aparece una sección nueva, en su orden y con su color | "Prevención y campañas" (orden 30) aparece después de "Atención de salud", con su tarjeta en naranja | Aprobado | Cliente |
| C-03 | Sin categoría | Quitar la categoría a un módulo | Aparece al final, en "Otras herramientas" | El módulo pasa a "Otras herramientas", que queda como última sección | Aprobado | Cliente |
| C-04 | Categoría vacía | Desactivar todos los módulos de una categoría | La sección no aparece | Con su único módulo desactivado, la sección no aparece | Aprobado | Cliente |
| C-05 | Buscar | Escribir "vacunacion", "REM" y "urgencia" | Filtra sin distinguir mayúsculas ni tildes, y oculta las secciones sin resultados | "vacunacion" → Campaña de invierno; "REM" → Indicadores IAAPS y REM; "URGENCIA" → Atenciones de urgencia. Solo queda visible la sección de cada resultado | Aprobado | Navegador |
| C-06 | Sin resultados | Buscar una palabra que no existe | "No hay herramientas con esa palabra" | Muestra el aviso y oculta todas las secciones | Aprobado | Navegador |
| C-07 | Buscador con lector de pantalla | Buscar con NVDA o Narrador | Anuncia "N herramientas encontradas" | La región `aria-live` cambia a "1 herramienta encontrada." y "0 herramientas encontradas.". Falta oírlo con NVDA o Narrador | Pendiente | Navegador (parcial) |
| C-08 | Etiqueta "Nuevo" | Marcar "Nuevo" en un módulo | La tarjeta muestra la etiqueta | Solo la tarjeta marcada muestra "Nuevo" | Aprobado | Cliente |
| C-09 | Tamaños de pantalla | Ver la portada en 1280, 768 y 375 px | Sin scroll horizontal; secciones y buscador legibles | Con 12 módulos, sin scroll horizontal en 1280, 768 y 375 px; secciones y buscador legibles | Aprobado | Navegador |

### Diseño de cuadritos (PR #9)

| ID | Caso | Pasos | Esperado | Obtenido | Estado | Evidencia |
|---|---|---|---|---|---|---|
| D-05 | Cuadritos por fila | Ver la portada en 1280, 768 y 375 px | 4, 3 y 2 tarjetas por fila; con un nombre de 80 caracteres y una descripción de 200, la fila crece y nada se sale | 4, 3 y 2 tarjetas por fila. La tarjeta de 80 y 200 caracteres mide 220 × 453 px en escritorio y 167 × 481 px en celular; ninguna tarjeta desborda | Aprobado | Navegador |
| D-06 | Colores de categoría | Ver una tarjeta de cada color y una "En preparación" | Fondo suave de su color y borde del mismo tono; "En preparación" sigue gris y punteada | Degradado de blanco al color claro de cada categoría, borde del mismo tono e ícono en el color fuerte. "En preparación": gris (#eef1f4), sin degradado y con borde punteado | Aprobado | Navegador |
| D-07 | Contraste sobre el fondo de color | Medir descripción y "Abrir" en la parte más oscura del fondo, en las cuatro categorías | 4,5:1 o más | El menor es 6,74:1 ("Abrir" sobre el morado). Descripciones: 7,69:1 o más; nombres: 12,37:1 o más | Aprobado | Navegador |
| D-08 | Sello con ícono | Ver el sello en la portada y en la lista de reportes | El ícono de calendario aparece en ambos y el lector de pantalla no lo lee | El ícono aparece en la portada y en la lista de reportes, con `aria-hidden="true"` | Aprobado | Navegador |
| D-09 | Reducir movimiento | Activar "reducir movimiento" en el sistema y pasar el mouse por una tarjeta | La tarjeta no se mueve | La hoja de estilos quita la transición y el desplazamiento con `prefers-reduced-motion: reduce`. No se activó la opción en Windows para verlo | Aprobado con observación | Revisión del CSS |

### Acceso por grupo (`feature/acceso-por-grupo`)

| ID | Caso | Pasos | Esperado | Obtenido | Estado | Evidencia |
|---|---|---|---|---|---|---|
| G-01 | Módulo sin grupos | Ingresar con una cuenta común sin grupos | Ve todos los módulos sin grupos | La cuenta sin grupos ve todos los módulos sin grupos | Aprobado | Cliente |
| G-02 | Módulo restringido | Asignar el grupo "Per Cápita" al módulo e ingresar con una cuenta que no es del grupo | No ve la tarjeta ni su corte en el sello | No ve la tarjeta de Per Cápita ni su corte en el sello | Aprobado | Cliente |
| G-03 | Miembro del grupo | Agregar la cuenta al grupo y volver a entrar | Ve la tarjeta y su corte | Ve la tarjeta y "Per Cápita Comunal: Noviembre 2026" | Aprobado | Cliente |
| G-04 | Enlace directo | Sin ser del grupo, abrir `/modulos/<id>/` y el enlace de descarga de uno de sus reportes | Página no encontrada en ambos | `/modulos/<id>/`, la descarga y `/modulos/<id>/abrir/` responden 404 | Aprobado | Cliente |
| G-05 | Superusuario | Ingresar con un superusuario | Ve todos los módulos | El superusuario ve todos los módulos | Aprobado | Cliente |
| G-06 | Columna "Acceso" | Abrir Administrar > Módulos | "Todos" o el nombre de los grupos | Muestra "Equipo Per Cápita" y "Todos" | Aprobado | Cliente |

### Registro de accesos (`feature/demo-registro-produccion`)

| ID | Caso | Pasos | Esperado | Obtenido | Estado | Evidencia |
|---|---|---|---|---|---|---|
| L-01 | Abrir un módulo | Hacer clic en una tarjeta con enlace | Se abre el enlace en otra pestaña y queda "Abrió el enlace" en Accesos registrados | Redirige al enlace del módulo y anota "Abrió el enlace" con la cuenta y el módulo | Aprobado | Cliente |
| L-02 | Reportes | Ver la lista de reportes y descargar uno | Quedan "Vio la lista de reportes" y "Descargó un reporte", con el período | Quedan "Vio la lista de reportes" y "Descargó un reporte" ("Indicadores IAAPS y REM: IAAPS comunal (Noviembre 2026)") | Aprobado | Cliente |
| L-03 | Solo consulta | En Accesos registrados, buscar "Añadir" o editar un registro | No se puede; un staff sin superusuario tampoco puede borrar | "Añadir" responde 403 y la ficha no tiene "Guardar". Un staff con todos los permisos del modelo ve la lista, pero borrar responde 403 | Aprobado | Cliente |
| L-04 | Limpieza | Correr `borrar_accesos_antiguos --dias 365` | Borra solo los de más de un año e informa cuántos | "Se borraron 1 registros anteriores al 25-11-2025."; el registro reciente se mantiene | Aprobado | Consola |

### Servidor (`feature/demo-registro-produccion`)

| ID | Caso | Pasos | Esperado | Obtenido | Estado | Evidencia |
|---|---|---|---|---|---|---|
| SV-01 | Revisión de Django | `manage.py check --deploy` en el servidor | "no issues (2 silenced)" | Requiere el servidor. En este equipo, con la configuración del servidor: "no issues (2 silenced)" | Pendiente | Consola (local) |
| SV-02 | Permisos | Con la cuenta de percapitados, intentar leer `db.sqlite3`, un archivo de `media/` y `respaldos/` | "Permiso denegado" en los tres | Requiere el servidor: en Windows los reportes quedan con permisos 666, porque Windows no aplica los permisos de Linux | Pendiente |  |
| SV-03 | Intentos en el panel | Enviar más de 20 ingresos fallidos seguidos a `/admin/login/` | Nginx responde 429, igual que en `/ingresar/` | Requiere el servidor con Nginx | Pendiente |  |
| SV-04 | Respaldo | Correr el respaldo del README y abrir la copia | La copia tiene los módulos y accesos; el `.tar.gz` tiene los reportes | Requiere el servidor | Pendiente |  |

### Observaciones de la primera pasada

| ID | Caso | Pasos | Esperado | Obtenido | Estado | Evidencia |
|---|---|---|---|---|---|---|
| O-01 | Nombre en el ingreso | Abrir `/ingresar/` | Dice "Repositorio Estadístico" sobre "Iniciar sesión" | Dice "Repositorio Estadístico" sobre "Iniciar sesión" | Aprobado | Cliente y navegador |
| O-02 | Bloq Mayús con lector de pantalla | Activar Bloq Mayús y escribir la clave con NVDA o Narrador | Anuncia "Bloq Mayús está activado" | El aviso queda en la página (`display: block`, alto 0) con `aria-live="polite"`. Falta oírlo con NVDA o Narrador | Pendiente | Navegador (parcial) |
| O-03 | A-04 en Chrome y Edge | Repetir A-04 en el computador de la demostración | No muestra la portada | A-04 se aprobó en Chromium. Falta Chrome o Edge del computador de la demostración | Pendiente |  |
| O-04 | Instalación con el README | Instalar desde cero siguiendo el README, incluida la sección "Si la instalación falla" | Queda listo. Si José repite el error, anotar el texto | Clonado de GitHub, instalado y migrado con Python 3.12.0. En este equipo `python` abre la Microsoft Store (Python no está en el PATH), lo que cubre la primera ayuda del README. Con `DJANGO_SECRET_KEY` vacía el sistema no arranca y el README no lo decía: se agregó | Aprobado con observación | Consola |

### Observaciones de la segunda pasada

- **El sello crece con cada módulo:** con 12 módulos ocupa toda la primera pantalla del celular, y el buscador y las tarjetas quedan más abajo. Conviene decidir si el sello muestra solo los módulos con corte o si se puede plegar.
- **Nombres largos:** una tarjeta con un nombre de 80 caracteres crece hasta 453 px de alto. Se lee bien, pero conviene usar nombres cortos.
- **Permisos de archivos:** en Windows no se pueden comprobar; quedan para SV-02 en el servidor.
- **Lectores de pantalla:** C-07 y O-02 quedaron revisados en el código de la página, pero falta oírlos con NVDA o Narrador.

### Recomendación de la segunda pasada

Se puede unir el PR #9 y mostrar a Cristian el portal completo con `cargar_demo`. Rendimientos se muestra solo después de que P-01 esté aprobado. Antes de usarlo con datos reales: instalar en el servidor y correr SV-01 a SV-04 y R-08, probar R-01 y R-02 con los reportes de Daniel, y O-03 en el computador de la demostración.
