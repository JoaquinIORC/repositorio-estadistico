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
