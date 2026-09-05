# =========================================================
# Archivo de configuración WSGI para PythonAnywhere
# =========================================================
# Copia el contenido de este archivo dentro del editor WSGI que
# PythonAnywhere te abre automáticamente en la pestaña "Web"
# (normalmente en /var/www/tuusuario_pythonanywhere_com_wsgi.py)
#
# Reemplaza "tuusuario" por tu nombre de usuario real de PythonAnywhere.
# =========================================================

import sys
import os

# 1. Ruta donde subiste el proyecto (ajusta "tuusuario")
project_home = '/home/tuusuario/tecuns-roofing'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# 2. Variables de entorno CRÍTICAS — definir ANTES de importar la app
# =============================================================
# En PythonAnywhere NO se usa archivo .env; las variables se definen
# aquí en el WSGI o en la consola Bash (export VAR=valor) y reload.

# Clave secreta de Flask (genera una larga y aleatoria)
os.environ.setdefault('SECRET_KEY', 'CAMBIA-ESTO-POR-UNA-CLAVE-LARGA-Y-UNICA')

# Cookies Secure solo con HTTPS
os.environ.setdefault('SESSION_COOKIE_SECURE', '1')

# URL base del sitio para sitemap.xml (ej. https://tuusuario.pythonanywhere.com)
os.environ.setdefault('SITE_URL', 'https://tuusuario.pythonanywhere.com')

# ---------------------------------------------------------
# Google reCAPTCHA (obligatorio para que funcione el formulario de reseñas)
# ---------------------------------------------------------
# Consigue tus claves en: https://www.google.com/recaptcha/admin/create
# - Label: "Tecuns Roofing"
# - Tipo: v2 (Checkbox) o v3 (Invisible)
# - Dominios: agrega "tuusuario.pythonanywhere.com" y tu dominio personalizado si tienes
# - Copia Site Key y Secret Key aquí:
os.environ.setdefault('RECAPTCHA_SITE_KEY', 'TU_RECAPTCHA_SITE_KEY_AQUI')
os.environ.setdefault('RECAPTCHA_SECRET_KEY', 'TU_RECAPTCHA_SECRET_KEY_AQUI')

# Versión: "v2" (checkbox visible) o "v3" (invisible, score-based)
os.environ.setdefault('RECAPTCHA_VERSION', 'v2')

# Score mínimo para v3 (0.0 - 1.0). 0.5 es balance razonable.
os.environ.setdefault('RECAPTCHA_MIN_SCORE', '0.5')

# ---------------------------------------------------------
# Listas anti-spam (opcional: usan valores por defecto si no se definen)
# ---------------------------------------------------------
# Palabras clave que marcan spam en comentarios
# os.environ.setdefault('SPAM_KEYWORDS', 'bitcoin,crypto,mining,click here,viagra,casino')

# Dominios de email temporales bloqueados
# os.environ.setdefault('SPAM_BLOCKED_DOMAINS', 'tempmail.com,10minutemail.com,mailinator.com')

# Acortadores de URL sospechosos
# os.environ.setdefault('SPAM_URL_SHORTENERS', 'bit.ly,tinyurl.com,goo.gl')

# 3. Importa la app Flask ya creada en app.py
# (Las variables de entorno arriba ya están cargadas en os.environ)
from app import app as application
