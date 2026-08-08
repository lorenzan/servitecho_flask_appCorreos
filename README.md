# Servitecho El Salvador — Sitio web + Panel de administración

Réplica funcional del sitio [servitecho.com.sv](https://servitecho.com.sv/index.html), construida
con **Flask** y **SQLite**, con 4 módulos adicionales:

- ⭐ **Reseñas** — los clientes dejan una reseña pública que **se publica de inmediato**; el administrador puede ocultarla o **eliminarla en cualquier momento** desde el panel.
- 📋 **Cotizaciones** — formulario donde el cliente indica su **ubicación** (con mapa interactivo tipo Google Maps para marcar el punto exacto, buscador de direcciones y botón "usar mi ubicación actual"), **descripción del trabajo** y puede **subir varias fotos** del proyecto. Un administrador las revisa, ve el punto en el mapa y cambia su estado.
- 🖼️ **Administración de contenido** — panel para editar **todas las imágenes y textos** editables del sitio: logotipo del header/footer, imagen del hero, imagen de "sobre nosotros", íconos de misión/visión/soporte, imagen de fondo de "¿Qué nos distingue?" y los datos de contacto. Las imágenes de los productos se administran desde su propio módulo (Productos / Servicios).
- ✉️ **Correo (Gmail SMTP)** — se te notifica por correo cada vez que llega una nueva reseña o cotización, puedes responder directamente al cliente por correo desde el detalle de la cotización, y todo se configura y personaliza desde el panel (sin tocar código).
- 🛠️ **Administración de productos/servicios** — CRUD de los productos (Standing Seam, Panel Termoacústico, Módulos Constructivos), cada uno con su propia página pública.

## 1. Requisitos

- Python 3.10 o superior

## 2. Instalación

```bash
cd servitecho
python3 -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Inicializar la base de datos (solo la primera vez)

```bash
python seed.py
```

Esto crea el archivo `instance/servitecho.db` con:

- Un usuario administrador:
  - **Usuario:** `admin`
  - **Contraseña:** `Servitecho2024!`
  - ⚠️ Cámbiala después de tu primer inicio de sesión (ver sección 6).
- Los 3 productos (Standing Seam, Panel Termoacústico, Módulos Constructivos).
- Los bloques de texto de la página de inicio (hero, misión, visión, etc.).
- 3 reseñas de ejemplo ya aprobadas.

## 4. Ejecutar la aplicación

```bash
python app.py
```

Abre tu navegador en **http://127.0.0.1:5000**

- Sitio público: `http://127.0.0.1:5000/`
- Panel de administrador: `http://127.0.0.1:5000/admin/login`

## 5. Estructura del proyecto

```
servitecho/
├── app.py                 # Application factory / punto de entrada
├── config.py               # Configuración (rutas, límites de subida)
├── extensions.py           # Instancias de SQLAlchemy / Flask-Login
├── models.py                # Modelos: Admin, ContentBlock, Service, Review, Quote, QuoteImage
├── public_routes.py         # Rutas del sitio público
├── admin_routes.py          # Rutas del panel de administración
├── utils.py                  # Helper para subir imágenes
├── seed.py                    # Script de datos iniciales
├── requirements.txt
├── static/
│   ├── css/style.css        # Estilos del sitio público
│   ├── css/admin.css        # Estilos del panel admin
│   └── uploads/
│       ├── content/          # Imágenes subidas desde "Contenido del sitio"
│       └── quotes/            # Fotos subidas por clientes en cotizaciones
├── templates/
│   ├── base.html, index.html, servicio_detalle.html, resenas.html,
│   │   cotizacion.html, cotizacion_gracias.html
│   └── admin/                 # Login, dashboard y CRUD del panel
└── instance/
    └── servitecho.db          # Base de datos SQLite (se genera con seed.py)
```

## 6. Cambiar la contraseña del administrador

Por seguridad, cambia la contraseña por defecto ejecutando en una consola de Python
(estando dentro de la carpeta del proyecto, con el entorno virtual activado):

```python
from app import create_app
from extensions import db
from models import Admin

app = create_app()
with app.app_context():
    admin = Admin.query.filter_by(username="admin").first()
    admin.set_password("TU_NUEVA_CONTRASEÑA_SEGURA")
    db.session.commit()
```

## 7. Módulos del panel de administración

| Sección | Qué puedes hacer |
|---|---|
| **Panel principal** | Resumen (KPIs) de cotizaciones y reseñas pendientes |
| **Reseñas** | Se publican automáticamente al enviarse; puedes ocultarlas o eliminarlas cuando lo necesites |
| **Cotizaciones** | Ver solicitudes con ubicación (mapa), descripción y fotos adjuntas; cambiar estado (pendiente → en revisión → cotizado / rechazado) y dejar notas internas |
| **Productos / Servicios** | Crear, editar, ocultar o eliminar los productos que aparecen en el sitio |
| **Contenido del sitio** | Editar el logotipo, y los textos e imágenes de cada sección de la página de inicio |
| **Correo — Configuración** | Activar/desactivar el envío de correos, definir el Gmail que envía, la contraseña de aplicación y a qué correo llegan las notificaciones |
| **Correo — Plantillas** | Editar el asunto y mensaje de los 3 correos automáticos (nueva reseña, nueva cotización, respuesta al cliente) |

## 8.1 Configurar el envío de correos (Gmail)

Todo se configura desde el panel, en **Correo → Configuración** (`/admin/configuracion/correo`), sin tocar código:

1. **Activa la verificación en 2 pasos** en la cuenta de Gmail que enviará los correos: [myaccount.google.com/security](https://myaccount.google.com/security)
2. Ve a [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) y crea una **contraseña de aplicación** nueva (por ejemplo, nómbrala "Servitecho Web"). Google te dará un código de 16 caracteres — cópialo.
   > ⚠️ Gmail ya no permite enviar correos usando la contraseña normal de la cuenta. Se necesita esta "contraseña de aplicación" (no es literalmente una "API key", pero cumple la misma función: autenticar el envío sin exponer tu contraseña real).
3. En el panel, entra a **Correo → Configuración** y llena:
   - ✅ Activar el envío de correos
   - **Correo de Gmail que envía los mensajes** → el Gmail donde generaste la contraseña de aplicación
   - **Contraseña de aplicación** → el código de 16 caracteres del paso 2
   - **Correo donde recibirás las notificaciones** → puede ser el mismo Gmail u otro correo tuyo
4. Guarda y presiona **"Enviar correo de prueba"** para confirmar que todo funciona.

### ¿Qué correos se envían automáticamente?
| Evento | Se le avisa a | Plantilla usada |
|---|---|---|
| Se publica una nueva reseña | Tu correo de notificaciones | "Notificación: nueva reseña" |
| Llega una nueva solicitud de cotización | Tu correo de notificaciones | "Notificación: nueva cotización" |
| Respondes una cotización desde el panel (botón "Enviar respuesta por correo") | El correo del cliente | "Respuesta de cotización (al cliente)" |

Las 3 plantillas se editan libremente desde **Correo → Plantillas**, incluyendo variables como `{{ nombre }}`, `{{ ubicacion }}`, `{{ respuesta }}`, etc. — cada plantilla muestra qué variables tiene disponibles.

⚠️ **Nota de seguridad:** la contraseña de aplicación se guarda en la base de datos SQLite del servidor. Esto es adecuado para un panel de un solo administrador; si en el futuro agregas más usuarios administradores, considera restringir quién puede ver/editar esta sección.

## 8. Notas técnicas

- El mapa de ubicación usa **Leaflet + OpenStreetMap** (gratuito, sin necesidad de una API key de Google). El cliente puede buscar una dirección, hacer clic en el mapa o usar su ubicación GPS; las coordenadas se guardan junto con la cotización y se muestran en un mapa dentro del panel admin, con enlaces directos a Google Maps y OpenStreetMap.
- Las imágenes se guardan en `static/uploads/` con nombres únicos (UUID) para evitar colisiones.
- Tamaño máximo de subida: 16 MB por solicitud (configurable en `config.py`).
- Formatos de imagen permitidos: `.png .jpg .jpeg .webp .gif`.
- El servidor incluido (`python app.py`) es de desarrollo. Para producción, usa un servidor WSGI como **Gunicorn** o **Waitress** detrás de Nginx, y cambia `SECRET_KEY` en `config.py` (o defínela como variable de entorno).

## 9. Próximos pasos sugeridos

- Sustituir las imágenes de ejemplo por fotos reales de proyectos (desde el panel de Contenido/Servicios).
- Conectar el envío de cotizaciones a un correo o WhatsApp automático (por ejemplo, con `Flask-Mail` o la API de WhatsApp Business).
- Agregar HTTPS y un dominio propio al desplegar en producción.

## 10. Desplegar en PythonAnywhere

### Paso 1 — Sube el proyecto
1. Crea tu cuenta en [pythonanywhere.com](https://www.pythonanywhere.com) e inicia sesión.
2. Ve a la pestaña **Files**, sube el archivo `servitecho_flask_app.zip` (o sube el proyecto vía GitHub con `git clone` desde una consola Bash).
3. Abre una consola **Bash** desde el Dashboard y descomprime:
   ```bash
   unzip servitecho_flask_app.zip -d servitecho
   cd servitecho
   ```

### Paso 2 — Crea el entorno virtual e instala dependencias
En la misma consola Bash:
```bash
mkvirtualenv --python=/usr/bin/python3.10 servitecho-venv
pip install -r requirements.txt
```
(Si `mkvirtualenv` no está disponible, usa `python3.10 -m venv servitecho-venv && source servitecho-venv/bin/activate`)

### Paso 3 — Inicializa la base de datos
```bash
python seed.py
```

### Paso 4 — Crea el Web App
1. Ve a la pestaña **Web** → **Add a new web app**.
2. Elige **Manual configuration** (no "Flask", para poder usar tu propio entorno virtual y dependencias).
3. Selecciona la misma versión de Python que usaste en el paso 2 (ej. 3.10).

### Paso 5 — Configura el Web App
En la página de configuración de tu Web App:

- **Source code:** `/home/tuusuario/servitecho`
- **Working directory:** `/home/tuusuario/servitecho`
- **Virtualenv:** `/home/tuusuario/.virtualenvs/servitecho-venv`
- **WSGI configuration file:** haz clic en el link para abrir el editor, borra el contenido y pega el de `wsgi_pythonanywhere_example.py` (incluido en este proyecto), ajustando `tuusuario` por tu usuario real.

En la sección **Static files**, agrega:
| URL | Directory |
|---|---|
| `/static/` | `/home/tuusuario/servitecho/static` |

### Paso 6 — Variables de entorno (opcional pero recomendado)
En la sección **Environment variables** de la pestaña Web, agrega:
- `SECRET_KEY` → una clave larga y aleatoria (o déjala definida directamente en el archivo WSGI, como en el ejemplo incluido).

### Paso 7 — Reload
Haz clic en el botón verde **Reload** en la parte superior de la pestaña Web. Tu sitio quedará disponible en `https://tuusuario.pythonanywhere.com`.

### Notas importantes para el plan gratuito
- El plan gratuito de PythonAnywhere solo permite conexiones salientes del **servidor** hacia una lista blanca de dominios. Esto **no afecta** al mapa de ubicación (Leaflet/OpenStreetMap/Nominatim), ya que esas peticiones las hace el **navegador del cliente**, no el servidor.
- El plan gratuito da 512 MB de espacio en disco — suficiente para empezar, pero si subes muchas fotos de cotizaciones, considera limpiarlas periódicamente o subir de plan.
- Cada vez que subas cambios de código, recuerda volver a presionar **Reload** en la pestaña Web para que se apliquen.
- El archivo `instance/servitecho.db` y la carpeta `static/uploads/` deben persistir entre despliegues — no los borres al actualizar el código, solo reemplaza los archivos `.py`, `.html` y `.css`.

