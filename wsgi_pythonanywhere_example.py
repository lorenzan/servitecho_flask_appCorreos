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
project_home = '/home/tuusuario/servitecho'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# 2. Variable de entorno para la SECRET_KEY (mejor que dejarla fija en config.py)
os.environ.setdefault('SECRET_KEY', 'CAMBIA-ESTO-POR-UNA-CLAVE-LARGA-Y-UNICA')

# 3. Importa la app Flask ya creada en app.py
from app import app as application
