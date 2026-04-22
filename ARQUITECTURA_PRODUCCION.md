# 🏗️ ARQUITECTURA DE PRODUCCIÓN - SISTEMA TPE v3.3
## Manual para Docente de Redes (Educativo)

---

## Tabla de Contenidos
1. [Conceptos Fundamentales](#1-conceptos-fundamentales)
2. [Arquitectura de Red](#2-arquitectura-de-red)
3. [Las 4 Capas de la Aplicación](#3-las-4-capas)
4. [Flujo de Datos Completo](#4-flujo-de-datos)
5. [Seguridad en Producción](#5-seguridad)
6. [Implementación Paso a Paso](#6-implementación)
7. [Resolución de Problemas](#7-resolución-de-problemas)
8. [Monitoreo y Mantenimiento](#8-monitoreo)

---

## 1. CONCEPTOS FUNDAMENTALES

### ¿Qué es Client-Server?

Una aplicación **Client-Server** funciona en dos máquinas diferentes:

- **Cliente (navegador):** Donde el usuario interactúa
- **Servidor:** Donde viven los datos y la lógica

### Analogía: Banco vs Sucursal

```
┌─────────────────┐         ┌──────────────────┐
│ CLIENTE (Usuario)          │ SERVIDOR          │
├─────────────────┤         ├──────────────────┤
│ Abre navegador  │         │ Django + MySQL   │
│ Llena formulario│  ←───→  │ Procesa datos    │
│ Envía datos     │         │ Guarda en BD     │
│ Ve resultado    │         │ Responde         │
└─────────────────┘         └──────────────────┘
      (En casa)                  (En oficina)
```

### ¿Por qué separar Cliente y Servidor?

| Ventaja | Razón |
|---------|-------|
| **Seguridad** | Datos guardados en lugar seguro (servidor) |
| **Escalabilidad** | Muchos clientes, 1 servidor |
| **Consistencia** | Una sola copia de la verdad (BD) |
| **Mantenimiento** | Cambios en servidor, no en cada PC |

---

## 2. ARQUITECTURA DE RED

### El Escenario: Red Local de la Oficina

```
                    LAN (Red Local - 192.168.1.0/24)
    ┌────────────────────────────────────────────────────┐
    │                                                    │
    │  🖥️ SERVIDOR TPE                                  │
    │  IP: 192.168.1.100                               │
    │  Puertos:                                         │
    │  ├─ 8000 (Django/Gunicorn)                        │
    │  ├─ 3306 (MySQL)                                 │
    │  └─ 22 (SSH - opcional)                          │
    │                                                    │
    │  USUARIOS CONECTADOS:                            │
    │  ├─ Abogado1 (PC) - IP: 192.168.1.50           │
    │  ├─ Abogado2 (Laptop) - IP: 192.168.1.51       │
    │  ├─ Admin (Tablet) - IP: 192.168.1.52          │
    │  └─ Vocal (Celular) - IP: 192.168.1.53         │
    │                                                    │
    │  🔐 ROUTER (Puerta de entrada)                   │
    │  IP: 192.168.1.1                                │
    │                                                    │
    └────────────────────────────────────────────────────┘
                        ↓ WiFi/Ethernet
            🌐 INTERNET (Bloqueado por Firewall)
```

### Capas de Red (OSI - 7 capas)

```
Capa 7: APLICACIÓN    ← Django (HTTP)
Capa 6: PRESENTACIÓN  ← HTML, CSS, JavaScript
Capa 5: SESIÓN        ← Cookies, Tokens
Capa 4: TRANSPORTE    ← TCP/Puerto 8000
Capa 3: RED           ← IP 192.168.1.100
Capa 2: ENLACE        ← WiFi/Ethernet
Capa 1: FÍSICA        ← Cables, señal WiFi
```

---

## 3. LAS 4 CAPAS DE LA APLICACIÓN

### Capa 1: PRESENTACIÓN (Frontend)

**¿Qué es?** Lo que ve el usuario en su navegador

**Componentes:**
- HTML (estructura)
- CSS (estilos)
- JavaScript (interactividad)
- Validación en cliente

**Responsabilidades:**
```html
<!-- ✅ VALIDAR datos antes de enviar -->
<input type="email" required>

<!-- ✅ PROTEGER contra CSRF -->
{% csrf_token %}

<!-- ✅ PROTEGER contraseñas -->
<input type="password" required>
```

**Ubicación:** En el navegador del cliente (descargado del servidor)

---

### Capa 2: LÓGICA (Backend)

**¿Qué es?** El "cerebro" de la aplicación (Django)

**Componentes:**
```
tpe_app/
├── views/
│   ├── admin1_views.py     ← Funciones que procesan solicitudes
│   ├── abogado_views.py    ← Lógica para abogados
│   └── ...
├── forms.py                ← Validación de formularios
└── decorators.py           ← @rol_requerido para permisos
```

**Responsabilidades:**

1. **Autenticación:** ¿El usuario es quien dice ser?
   ```python
   user = authenticate(username='abogado1', password='pass')
   if user:
       login(request, user)  # ✅ Correcto
   else:
       return HttpResponse("Credenciales inválidas")  # ❌
   ```

2. **Autorización:** ¿Puede hacer lo que pide?
   ```python
   @rol_requerido('ABOG')
   def crear_dictamen(request):
       # Solo abogados llegan aquí
   ```

3. **Validación:** ¿Los datos son correctos?
   ```python
   form = DictamenForm(request.POST)
   if form.is_valid():
       # Procesar
   else:
       # Mostrar errores
   ```

4. **Procesamiento:** Aplicar reglas de negocio
   ```python
   # Ejemplo: generar número automático
   DIC_NUM = f"{max_numero + 1:03d}/26"
   ```

**Ubicación:** En el servidor

---

### Capa 3: MODELOS (Estructura de Datos)

**¿Qué es?** La definición de tablas y relaciones

**Componentes:**
```python
class SIM(models.Model):
    SIM_ID = models.AutoField(primary_key=True)
    SIM_NUM = models.CharField(max_length=20)
    SIM_OBJETO = models.TextField()
    SIM_FECEMISION = models.DateField(auto_now_add=True)
    SIM_ESTADO = models.CharField(
        max_length=50,
        choices=[
            ('PARA_AGENDA', 'Pendiente Agenda'),
            ('PROCESO_EN_EL_TPE', 'En Proceso'),
        ]
    )
    
    def save(self, *args, **kwargs):
        # Validación: convertir a mayúsculas
        self.SIM_OBJETO = self.SIM_OBJETO.upper()
        super().save(*args, **kwargs)
```

**Responsabilidades:**
- Validación de datos antes de guardar
- Relaciones entre tablas (ForeignKey)
- Métodos de lógica de modelos

**Ubicación:** Define la estructura en MySQL

---

### Capa 4: DATOS (Base de Datos)

**¿Qué es?** Almacenamiento permanente (MySQL)

**Componentes:**
```
Tablas:
├── pm              ← Personal Militar
├── sim             ← Sumarios Informativos
├── abog            ← Abogados
├── dictamen        ← Dictámenes
├── res             ← Resoluciones
├── autotpe         ← Autos del TPE
└── custodias_sim   ← Control de carpetas
```

**Responsabilidades:**
- Almacenar datos de forma segura
- Permitir búsquedas rápidas (índices)
- Mantener integridad referencial
- Manejar transacciones

**Ubicación:** En el servidor (archivos .ibd)

---

## 4. FLUJO DE DATOS COMPLETO

### Ejemplo: Abogado crea un Dictamen

```
PASO 1: USUARIO ABRE LA PÁGINA
├─ Abre navegador: http://192.168.1.100:8000
├─ El navegador envía petición HTTP GET
└─ Viaja por cable/WiFi al servidor

PASO 2: SERVIDOR RECIBE PETICIÓN
├─ Django escucha en puerto 8000
├─ Interpreta la URL: /abogado/dictamen/crear/
└─ Busca la función correspondiente en abogado_views.py

PASO 3: DJANGO PROCESA LA PETICIÓN
├─ Verifica: ¿Está logged in?
│  └─ Lee cookie SESSIONID en el navegador
│  └─ Busca esa sesión en Django
├─ Verifica: ¿Tiene rol ABOG?
│  └─ Consulta tabla auth_user
│  └─ ✅ Sí → Continúa
│  └─ ❌ No → Redirige a login
└─ Genera un formulario vacío

PASO 4: SERVIDOR ENVÍA HTML AL NAVEGADOR
├─ HTML contiene:
│  ├─ Formulario con campos
│  ├─ Token CSRF (protección)
│  └─ JavaScript para validación
└─ Navegador recibe y muestra

PASO 5: USUARIO LLENA FORMULARIO
├─ Escribe número del sumario
├─ Escribe texto del dictamen
└─ Presiona "Guardar"

PASO 6: NAVEGADOR VALIDA (JavaScript)
├─ ¿Campo vacío? ✅ No
├─ ¿Demasiado corto? ✅ No
└─ ✅ OK → Envía al servidor

PASO 7: NAVEGADOR ENVÍA DATOS
├─ Método: POST (no GET, por seguridad)
├─ Datos incluyen:
│  ├─ csrfmiddlewaretoken (protección)
│  ├─ SIM_ID
│  └─ DIC_TEXTO
└─ Viaja encriptado por HTTPS (idealmente)

PASO 8: SERVIDOR RECIBE DATOS
├─ Verifica CSRF token
│  └─ ❌ Inválido → Rechaza (ataque detectado)
│  └─ ✅ Válido → Continúa
├─ Verifica sesión de usuario
│  └─ Valida que siga siendo abogado1
├─ Procesa formulario
│  └─ Crea objeto DictamenForm con los datos
└─ Valida formulario
   ├─ Verifica que SIM_ID existe
   ├─ Verifica que DIC_TEXTO no es vacío
   ├─ ❌ Error → Muestra en formulario
   └─ ✅ OK → Continúa

PASO 9: DJANGO APLICA LÓGICA
├─ Convierte DIC_TEXTO a MAYÚSCULAS
├─ Genera número automático: DIC_NUM = "001/26"
├─ Calcula DIC_FECEMISION = hoy (2026-04-22)
├─ Obtiene el usuario logueado: abogado1
└─ Crea objeto Dictamen en memoria

PASO 10: DJANGO VALIDA MODELO
├─ Ejecuta el método save() de Dictamen
├─ Verifica restricciones:
│  ├─ DIC_NUM es único (no duplicado)
│  ├─ SIM_ID existe (integridad referencial)
│  └─ Todos los campos requeridos presentes
└─ ✅ Todo OK

PASO 11: GUARDA EN BASE DE DATOS
├─ Django genera SQL INSERT:
│  ```
│  INSERT INTO dictamen (
│    DIC_NUM, DIC_TEXTO, ABOG_ID, SIM_ID, DIC_FECEMISION
│  ) VALUES (
│    '001/26', 'CONSIDERANDO QUE...', 2, 15, '2026-04-22'
│  )
│  ```
├─ MySQL ejecuta INSERT
├─ Guarda en tabla dictamen (archivo .ibd)
├─ Retorna ID = 245 (identificador único)
└─ ✅ Guardado exitosamente

PASO 12: SERVIDOR PROCESA RESPUESTA
├─ Obtiene ID del dictamen creado (245)
├─ Genera URL: /abogado/dictamen/245/
├─ Crea respuesta HTTP 302 (redirección)
└─ Envía al navegador

PASO 13: NAVEGADOR RECIBE RESPUESTA
├─ Lee código HTTP 302
├─ Automáticamente ve que debe ir a: /abogado/dictamen/245/
├─ Envía GET a esa URL
└─ Servidor responde con HTML del dictamen creado

PASO 14: USUARIO VE EL RESULTADO
├─ Navegador muestra: "✓ Dictamen creado exitosamente"
├─ Muestra tabla con el nuevo dictamen
├─ Abogado puede hacer clic para editarlo
└─ ✅ Proceso completo

TOTAL: ~500ms (medio segundo)
```

### Diagrama de Secuencia

```
Usuario          Navegador        Django         MySQL
  │                 │              │              │
  │─ Clic ─────────→│              │              │
  │             Envía GET          │              │
  │                 │─────────────→│              │
  │                 │              │ Verifica     │
  │                 │              │ sesión       │
  │                 │              │              │
  │                 │ HTML (formulario)          │
  │                 │←─────────────│              │
  │ Ve formulario   │              │              │
  │                 │              │              │
  │─ Llena ─────→  │              │              │
  │─ Presiona ────→│              │              │
  │  "Guardar"      │ Envía POST   │              │
  │                 │─────────────→│              │
  │                 │              │ Valida      │
  │                 │              │ formulario  │
  │                 │              │              │
  │                 │              │─ INSERT ────→│
  │                 │              │              │
  │                 │              │ ✓ OK        │
  │                 │              │←─────────────│
  │                 │ Redirección  │              │
  │                 │←─────────────│              │
  │ Ve resultado    │              │              │
  │←─ Muestra ─────│              │              │
  │   página        │              │              │
```

---

## 5. SEGURIDAD EN PRODUCCIÓN

### Los 7 Pilares de Seguridad

#### 1️⃣ AUTENTICACIÓN (¿Quién eres?)

```python
# ✅ CORRECTO
from django.contrib.auth import authenticate, login

username = request.POST['username']
password = request.POST['password']

user = authenticate(username=username, password=password)
if user is not None:
    login(request, user)  # Crea sesión segura
    return redirect('dashboard')
else:
    messages.error(request, "Credenciales inválidas")
```

**Lo que pasa detrás:**
```
1. Django recibe: username='abogado1', password='pass123'
2. Busca en BD: SELECT * FROM auth_user WHERE username='abogado1'
3. Obtiene: password_hash='pbkdf2_sha256$...'
4. Compara: bcrypt('pass123') == 'pbkdf2_sha256$...'
5. ✅ Coincide → Crea sesión
   ❌ No coincide → Rechaza
```

#### 2️⃣ AUTORIZACIÓN (¿Qué puedes hacer?)

```python
# ✅ DECORADOR: Solo abogados
@rol_requerido('ABOG')
def crear_dictamen(request):
    # Si no eres ABOG, Django redirecciona a login
    ...

# ✅ VERIFICACIÓN en la vista
def crear_resolución(request):
    if request.user.rol != 'ABOG':
        raise PermissionDenied("No tienes permiso")
    ...

# ✅ EN TEMPLATES (HTML)
{% if user.rol == 'ABOG' %}
    <button>Crear Dictamen</button>
{% endif %}
```

#### 3️⃣ VALIDACIÓN (¿Son correctos los datos?)

```python
# ✅ Formulario Django
class DictamenForm(forms.ModelForm):
    class Meta:
        model = Dictamen
        fields = ['SIM', 'DIC_TEXTO']
    
    def clean(self):
        cleaned_data = super().clean()
        sim = cleaned_data.get('SIM')
        
        # Validación personalizada
        if sim and sim.SIM_ESTADO == 'CONCLUIDO':
            raise forms.ValidationError("SIM ya está concluido")
        
        return cleaned_data

# En la vista:
if form.is_valid():
    form.save()  # Solo si TODO es válido
else:
    # Mostrar errores en formulario
```

#### 4️⃣ ENCRIPTACIÓN EN TRÁNSITO (HTTPS)

```
❌ SIN HTTPS:
Usuario: http://192.168.1.100:8000/login
         Contraseña viaja en TEXTO PLANO
         Cualquiera en la red puede leerla

✅ CON HTTPS:
Usuario: https://192.168.1.100:8000/login
         Contraseña viaja ENCRIPTADA
         Certificado SSL/TLS asegura conexión
```

**Para red local:**
- Opcional (mismo edificio, cables seguros)
- Recomendado (equipos móviles)

**Para internet:**
- OBLIGATORIO (https, no http)

#### 5️⃣ ENCRIPTACIÓN EN REPOSO (BD)

```sql
-- ❌ NUNCA guardar contraseñas en texto plano
INSERT INTO auth_user (username, password)
VALUES ('abogado1', 'pass123');  ← NUNCA

-- ✅ SIEMPRE usar HASH
INSERT INTO auth_user (username, password)
VALUES ('abogado1', 'pbkdf2_sha256$600000$abc$xyz');
```

**Django maneja esto automáticamente:**
```python
user = User.objects.create_user(
    username='abogado1',
    password='pass123'  # Django lo encripta automáticamente
)
# Se guarda como: pbkdf2_sha256$600000$salt$hash
```

#### 6️⃣ PROTECCIÓN CSRF (Cross-Site Request Forgery)

```html
<!-- ❌ INSEGURO: Sin CSRF token -->
<form method="POST">
    <input type="text" name="nombre">
    <button>Guardar</button>
</form>

<!-- ✅ SEGURO: Con CSRF token -->
<form method="POST">
    {% csrf_token %}  ← TOKEN ÚNICO POR SESIÓN
    <input type="text" name="nombre">
    <button>Guardar</button>
</form>
```

**Cómo funciona:**
```
1. Usuario obtiene formulario
   → Django genera token único: abc123xyz
   → Inserta en formulario HTML

2. Usuario envía formulario
   → Navegador incluye token en POST

3. Django recibe POST
   → Verifica: ¿El token coincide con la sesión?
   → ✅ Sí → Procesa
   → ❌ No → Rechaza (probablemente ataque)
```

#### 7️⃣ CONTROL DE ACCESO A NIVEL RED

```
┌─────────────────────────────────────────┐
│ FIREWALL DEL ROUTER (192.168.1.1)      │
├─────────────────────────────────────────┤
│ REGLAS:                                  │
│                                          │
│ ✅ PERMITIR:                            │
│  ├─ Tráfico interno 192.168.1.0/24      │
│  ├─ Puerto 8000 (Django)                │
│  └─ Puerto 3306 (MySQL) - red local     │
│                                          │
│ ❌ BLOQUEAR:                            │
│  ├─ Acceso desde internet externo       │
│  ├─ Puertos no autorizados              │
│  └─ Protocolos peligrosos               │
└─────────────────────────────────────────┘
```

**Verificar firewall (Windows):**
```bash
# Ver reglas activas
netsh advfirewall firewall show rule name=all

# Permitir puerto 8000
netsh advfirewall firewall add rule \
  name="Django TPE" \
  dir=in \
  action=allow \
  protocol=tcp \
  localport=8000

# Permitir solo desde red local
netsh advfirewall firewall add rule \
  name="Django Local Only" \
  dir=in \
  action=allow \
  protocol=tcp \
  localport=8000 \
  remoteip="192.168.1.0/24"
```

---

## 6. IMPLEMENTACIÓN PASO A PASO

### Fase 1: Preparación del Servidor (Una sola vez)

#### 1.1 Instalar Dependencias

```bash
# Python 3.11+ ya debe estar instalado

# Instalar paquetes necesarios
pip install django
pip install gunicorn
pip install mysql-connector-python
pip install python-dotenv

# Verificar
python --version       # Python 3.11+
django-admin --version # Django 4.2+
gunicorn --version     # gunicorn 21.2+
```

#### 1.2 Crear Archivo .env (Credenciales)

```bash
# Archivo: C:\proyectos\TPEsystem\.env
SECRET_KEY=django-insecure-ab1cd2ef3gh4ij5kl6mn7op8qr9stu0vwxyz1234567890ABC
DEBUG=False
ALLOWED_HOSTS=192.168.1.100,localhost,127.0.0.1

DB_ENGINE=django.db.backends.mysql
DB_NAME=tpe_system
DB_USER=usuario_tpe
DB_PASSWORD=ContraseñaSegura$%&123
DB_HOST=192.168.1.100
DB_PORT=3306

# Seguridad
SECURE_BROWSER_XSS_FILTER=True
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
```

**Importante:** Añadir .env a .gitignore

```bash
# .gitignore
.env
.env.local
*.pyc
__pycache__/
db.sqlite3
/staticfiles/
/media/
```

#### 1.3 Configurar settings.py

```python
# config/settings.py

import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# SEGURIDAD
SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.getenv(
    'ALLOWED_HOSTS',
    'localhost,127.0.0.1'
).split(',')

# BASE DE DATOS
DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.mysql'),
        'NAME': os.getenv('DB_NAME', 'tpe_system'),
        'USER': os.getenv('DB_USER', 'usuario_tpe'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', '192.168.1.100'),
        'PORT': os.getenv('DB_PORT', '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
        }
    }
}

# SESIONES Y SEGURIDAD
SESSION_COOKIE_AGE = 3600  # 1 hora
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True') == 'True'
SESSION_COOKIE_HTTPONLY = os.getenv('SESSION_COOKIE_HTTPONLY', 'True') == 'True'
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'True') == 'True'

# ARCHIVOS ESTÁTICOS
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# LOGS
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}
```

#### 1.4 Crear Base de Datos MySQL

```sql
-- En el servidor MySQL (cmd)
mysql -u root -p

-- Crear BD
CREATE DATABASE tpe_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Crear usuario solo para red local
CREATE USER 'usuario_tpe'@'192.168.1.%' IDENTIFIED BY 'ContraseñaSegura$%&123';

-- Dar permisos (NO todo)
GRANT SELECT, INSERT, UPDATE, DELETE ON tpe_system.* TO 'usuario_tpe'@'192.168.1.%';

-- NO permitir cambiar estructura
REVOKE ALTER, DROP, CREATE ON tpe_system.* FROM 'usuario_tpe'@'192.168.1.%';

-- Aplicar cambios
FLUSH PRIVILEGES;

-- Verificar
SHOW GRANTS FOR 'usuario_tpe'@'192.168.1.%';

-- Salir
EXIT;
```

#### 1.5 Ejecutar Migraciones

```bash
# En C:\proyectos\TPEsystem

# Crear carpeta de logs
mkdir logs

# Ejecutar migraciones
python manage.py makemigrations
python manage.py migrate

# Respuesta esperada:
# Operations to perform:
#   Apply all migrations: admin, auth, tpe_app, ...
# Running migrations:
#   Applying auth.0001_initial... OK
#   Applying tpe_app.0001_initial... OK
```

#### 1.6 Crear Superusuario (Admin)

```bash
python manage.py createsuperuser

# Respuesta esperada:
# Username: admin_tpe
# Email: admin@tpe.local
# Password: ContraseñaSegura123

# Crear otros usuarios por rol:
python manage.py shell
>>> from django.contrib.auth.models import User, Group
>>> # Crear grupos de permisos
>>> admin1_group = Group.objects.create(name='ADMIN1')
>>> abog_group = Group.objects.create(name='ABOG')
>>> vocal_group = Group.objects.create(name='VOCAL')
```

---

### Fase 2: Recolectar Archivos Estáticos

```bash
# En C:\proyectos\TPEsystem

python manage.py collectstatic --noinput

# Respuesta:
# You have requested to collect static files at the destination
# location as specified in your settings.
# 
# Processing... 123 static files
# POST-processed 123 files
```

---

### Fase 3: Iniciar el Servidor

#### Opción A: Gunicorn (Recomendado)

```bash
# Terminal 1: Django con Gunicorn
cd C:\proyectos\TPEsystem

gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --timeout 120 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log

# Respuesta esperada:
# [2026-04-22 14:30:22 +0000] Starting gunicorn 21.2.0
# [2026-04-22 14:30:23 +0000] Listening at: http://0.0.0.0:8000 (PID 1234)
# [2026-04-22 14:30:23 +0000] Worker spawned (pid: 1235)
# [2026-04-22 14:30:23 +0000] Worker spawned (pid: 1236)
# [2026-04-22 14:30:23 +0000] Worker spawned (pid: 1237)
# [2026-04-22 14:30:23 +0000] Worker spawned (pid: 1238)
```

#### Opción B: Django Development (Solo pruebas)

```bash
python manage.py runserver 0.0.0.0:8000

# ⚠️ NOTA: Solo para desarrollo
# NO usar en producción (es inseguro y lento)
```

---

### Fase 4: Configurar Firewall

```bash
# Windows Command Prompt (como administrador)

# Permitir puerto 8000 desde red local
netsh advfirewall firewall add rule ^
  name="Django TPE" ^
  dir=in ^
  action=allow ^
  protocol=tcp ^
  localport=8000 ^
  remoteip=192.168.1.0/24

# Verificar
netsh advfirewall firewall show rule name="Django TPE"
```

---

### Fase 5: Acceso desde Clientes

#### En otra PC (Windows)

```
1. Abre navegador (Firefox, Chrome, Edge)
2. Escribe: http://192.168.1.100:8000
3. Ves login del TPE
4. Escribe credenciales: abogado1 / pass123
5. ✅ Ves dashboard
```

#### En Tablet/Celular

```
1. Conecta al WiFi de la oficina
2. Abre navegador
3. Escribe: http://192.168.1.100:8000
4. Funciona igual
```

---

## 7. RESOLUCIÓN DE PROBLEMAS

### Problema 1: "No puedo acceder desde otra PC"

```bash
# PASO 1: Verificar IP del servidor
ipconfig /all

Resultados esperados:
  IPv4 Address. . . . . . . . . : 192.168.1.100
  Subnet Mask . . . . . . . . . : 255.255.255.0
  Default Gateway . . . . . . . : 192.168.1.1
```

```bash
# PASO 2: Verificar que Gunicorn está corriendo
netstat -ano | findstr :8000

Resultado esperado:
  TCP    0.0.0.0:8000    0.0.0.0:0    LISTENING    1234
  (1234 es el PID del proceso)
```

```bash
# PASO 3: Ping desde la otra PC
ping 192.168.1.100

Resultado esperado:
  Reply from 192.168.1.100: bytes=32 time=1ms TTL=128
  (Si no responde, hay problema de red)
```

```bash
# PASO 4: Probar conexión al puerto
telnet 192.168.1.100 8000

Resultado esperado:
  Attempting to connect to 192.168.1.100:8000 ...
  Connected to 192.168.1.100.
  Escape character is ']'.
```

```bash
# PASO 5: Si todo OK, abre navegador en otra PC
http://192.168.1.100:8000

Si ves ERROR en lugar de página:
  → Ir a siguiente problema
```

---

### Problema 2: "Me pide contraseña pero nunca entra"

```bash
# PASO 1: Verificar que BD está corriendo
mysql -u usuario_tpe -p -h 192.168.1.100

Ingresa: ContraseñaSegura$%&123

Resultado esperado:
  Welcome to the MySQL monitor.  Commands end with ; or \g.
  mysql>
```

```bash
# PASO 2: Verificar que BD y tabla existen
mysql> USE tpe_system;
mysql> SHOW TABLES;

Resultado esperado:
  auth_user
  auth_group
  tpe_app_pm
  tpe_app_sim
  ... más tablas ...
```

```bash
# PASO 3: Verificar usuario Django existe
mysql> SELECT username, password FROM auth_user;

Resultado esperado:
  admin_tpe | pbkdf2_sha256$600000$...
  abogado1  | pbkdf2_sha256$600000$...
```

```bash
# PASO 4: Ver logs de Django
# Archivo: C:\proyectos\TPEsystem\logs\django.log

[2026-04-22 14:35:22] ERROR: User authentication failed for username=abogado1
(busca líneas con ERROR)
```

```bash
# PASO 5: Probar login desde shell Django
python manage.py shell

>>> from django.contrib.auth.models import User
>>> user = User.objects.get(username='abogado1')
>>> user.check_password('pass123')
True   # ✅ Contraseña correcta
False  # ❌ Contraseña incorrecta
```

```bash
# PASO 6: Si contraseña es incorrecta, restablecerla
>>> user.set_password('nuevo_password')
>>> user.save()
>>> exit()
```

---

### Problema 3: "Base de datos rechaza conexión"

```bash
# PASO 1: Verificar que MySQL está corriendo
netstat -ano | findstr :3306

Resultado esperado:
  TCP    0.0.0.0:3306    0.0.0.0:0    LISTENING    2048
```

```bash
# PASO 2: Ver error exacto en logs
cat C:\proyectos\TPEsystem\logs\error.log

Mensajes comunes:
  - "Access denied for user 'usuario_tpe'@'192.168.x.x'"
    → Contraseña incorrecta en .env
  
  - "Can't connect to MySQL server on '192.168.1.100':3306"
    → MySQL no está corriendo o IP incorrecta
  
  - "Unknown database 'tpe_system'"
    → BD no fue creada
```

```bash
# PASO 3: Verificar credenciales en .env
cat .env | findstr DB_

Resultado:
  DB_NAME=tpe_system
  DB_USER=usuario_tpe
  DB_PASSWORD=ContraseñaSegura$%&123
  DB_HOST=192.168.1.100
  DB_PORT=3306
```

```bash
# PASO 4: Probar conexión manual
mysql -u usuario_tpe -p -h 192.168.1.100 -P 3306 tpe_system

Ingresa contraseña: ContraseñaSegura$%&123

Resultado esperado:
  mysql> 
  (sin errores)
```

---

### Problema 4: "Formularios lentos o se cuelgan"

```bash
# PASO 1: Ver procesos de Python
tasklist | findstr python

# Ver que Gunicorn está usando CPU
# Si CPU > 80%, hay problema de performance
```

```bash
# PASO 2: Aumentar workers de Gunicorn
# Si hay muchos usuarios, aumenta workers

gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 8          ← Cambiar de 4 a 8
  --worker-class sync  ← O usar async si hay conexiones lentas
  --timeout 120
```

```bash
# PASO 3: Ver consultas lentas en logs
cat logs/django.log | findstr DEBUG

(busca consultas que tarden > 1 segundo)
```

```bash
# PASO 4: Crear índices en BD para tablas grandes
mysql> USE tpe_system;
mysql> CREATE INDEX idx_sim_estado ON sim(SIM_ESTADO);
mysql> CREATE INDEX idx_abog_sim ON abog_sim(SIM_ID, ABOG_ID);
```

---

## 8. MONITOREO Y MANTENIMIENTO

### Monitoreo Diario

#### Script de verificación (PowerShell)

```powershell
# archivo: monitor_tpe.ps1

Write-Host "=== MONITOREO SERVIDOR TPE ===" -ForegroundColor Green

# 1. Verificar Gunicorn
Write-Host "`n1. Estado de Gunicorn:"
$gunicorn = Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.Name -like "*gunicorn*"}
if ($gunicorn) {
    Write-Host "✅ Gunicorn corriendo (PID: $($gunicorn.Id))"
} else {
    Write-Host "❌ Gunicorn NO está corriendo"
}

# 2. Verificar MySQL
Write-Host "`n2. Estado de MySQL:"
$mysql = Get-Process mysqld -ErrorAction SilentlyContinue
if ($mysql) {
    Write-Host "✅ MySQL corriendo (PID: $($mysql.Id))"
} else {
    Write-Host "❌ MySQL NO está corriendo"
}

# 3. Verificar conexión
Write-Host "`n3. Prueba de conexión:"
$test = Test-NetConnection -ComputerName 192.168.1.100 -Port 8000 -WarningAction SilentlyContinue
if ($test.TcpTestSucceeded) {
    Write-Host "✅ Puerto 8000 accesible"
} else {
    Write-Host "❌ Puerto 8000 NO accesible"
}

# 4. Ver uso de CPU y RAM
Write-Host "`n4. Recursos:"
Get-Process python | Select-Object Name, CPU, Memory | Format-Table
```

Ejecutar cada mañana:
```powershell
cd C:\proyectos\TPEsystem
powershell -ExecutionPolicy Bypass -File monitor_tpe.ps1
```

### Backup Automático

```powershell
# archivo: backup_tpe.ps1

$date = Get-Date -f "yyyyMMdd_HHmm"
$backup_dir = "D:\backups_TPE"

# Crear directorio si no existe
New-Item -ItemType Directory -Path $backup_dir -Force

# Backup de BD
mysqldump -u usuario_tpe -p"ContraseñaSegura$%&123" tpe_system | Out-File "$backup_dir\tpe_$date.sql"

# Backup de código
robocopy "C:\proyectos\TPEsystem" "$backup_dir\codigo_$date" /E /XD ".git" "__pycache__" ".venv"

# Limpiar backups > 7 días
Get-ChildItem $backup_dir -Filter "tpe_*.sql" | Where-Object {$_.LastWriteTime -lt (Get-Date).AddDays(-7)} | Remove-Item

Write-Host "✅ Backup realizado: $date"
```

Programar para ejecutar cada noche a las 19:50.

### Logs a Revisar

```bash
# Errores de Django
cat logs/django.log | Select-String "ERROR"

# Accesos a la aplicación
cat logs/access.log | tail -20

# Errores de MySQL
# En Windows: C:\ProgramData\MySQL\MySQL Server 8.0\Data\{nombre_servidor}.err
```

### Mantenimiento Mensual

- [ ] Revisar logs de errores
- [ ] Verificar espacio en disco
- [ ] Actualizar dependencias: `pip list --outdated`
- [ ] Revisar rendimiento de BD
- [ ] Realizar backup completo a almacenamiento externo
- [ ] Probar recuperación de backup

---

## RESUMEN FINAL

```
Usuario en otra PC
       ↓ (escribe http://192.168.1.100:8000)
    🔐 Firewall permite
       ↓
    📡 Router dirige al servidor
       ↓
🖥️ SERVIDOR Django (Gunicorn)
   ├─ Verifica usuario/contraseña
   ├─ Verifica rol (ABOG, ADMIN, etc.)
   ├─ Valida formulario
   └─ Procesa lógica
       ↓
🗄️ MYSQL
   ├─ Busca datos
   ├─ Guarda datos
   └─ Devuelve resultados
       ↓
🖥️ SERVIDOR responde
       ↓
💻 Navegador del usuario
       ↓
👤 Usuario ve su dashboard
```

**Cada flecha = validación de seguridad**

---

## REFERENCIAS Y RECURSOS

- Django Documentation: https://docs.djangoproject.com/
- MySQL Documentation: https://dev.mysql.com/doc/
- Gunicorn Documentation: https://gunicorn.org/
- OWASP Security: https://owasp.org/www-project-top-ten/
- Windows Firewall: https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/

---

**Última actualización:** 2026-04-22
**Versión:** 1.0 - Sistema TPE v3.3
**Autor:** Sistema de Documentación Automática
