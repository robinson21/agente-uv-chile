# Agente UV y Alertas Climáticas - Chile

Agente automatizado que consulta diariamente la radiación UV y condiciones climáticas para 8 ciudades chilenas, genera recomendaciones de Seguridad y Salud Ocupacional (SST/ESST), detecta alertas de calor extremo y condiciones adversas, y envía un reporte por correo electrónico.

## Ciudades monitoreadas

- Iquique
- Chañaral
- Coquimbo
- Maipú
- Santiago
- Talcahuano
- Puerto Montt
- Aysén

## Características

- **Índice UV**: Clasificación según estándares OMS con recomendaciones SST
- **Alertas automáticas**:
  - Calor extremo (≥ 33°C)
  - Precipitación intensa (≥ 70% probabilidad)
  - Tormentas eléctricas
  - UV Extremo (≥ 11)
- **Reporte HTML**: Formateado profesional para copiar y pegar en Microsoft Teams
- **Ejecución programada**: GitHub Actions ejecuta el agente de lunes a viernes a las 7:00 AM (hora Chile)

## Requisitos

- Python 3.9+
- Cuenta de Gmail con contraseña de aplicación
- GitHub (para ejecución automática)

## Configuración en GitHub

### Paso 1: Crear el repositorio

```bash
git init
git add .
git commit -m "Agente UV - Reporte diario de radiación UV y clima para Chile"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/agente-uv-chile.git
git push -u origin main
```

### Paso 2: Configurar secrets en GitHub

1. Ve a tu repositorio en GitHub
2. Clic en **Settings** → **Secrets and variables** → **Actions**
3. Clic en **New repository secret**
4. Agrega estos 3 secrets:

| Nombre | Valor |
|--------|-------|
| `GMAIL_USER` | Tu correo Gmail (ej: `tu_correo@gmail.com`) |
| `GMAIL_APP_PASSWORD` | Contraseña de aplicación de 16 caracteres |
| `EMAIL_DESTINO` | Correo destino (ej: `robinson.armijo@esmax.cl`) |

### Paso 3: Verificar GitHub Actions

- El workflow está configurado en `.github/workflows/agente_uv.yml`
- Se ejecuta de **lunes a viernes a las 10:00 UTC** (7:00 AM Chile)
- Puedes ejecutarlo manualmente desde la pestaña **Actions** → **Run workflow**

## Cómo obtener la contraseña de aplicación de Gmail

1. Ve a https://myaccount.google.com/apppasswords
2. Inicia sesión con tu cuenta de Gmail
3. Si tienes 2FA activado, crea una contraseña de aplicación:
   - Selecciona "Correo" como la aplicación
   - Selecciona tu dispositivo
   - Google generará una contraseña de 16 caracteres
4. Copia esa contraseña y úsala en `GMAIL_APP_PASSWORD`

**Nota**: Esta contraseña es diferente de tu contraseña normal de Gmail.

## Ejecución local (opcional)

### Instalación

```bash
pip install -r requirements.txt
```

### Configurar variables de entorno

```bash
export GMAIL_USER=tu_correo@gmail.com
export GMAIL_APP_PASSWORD=tu_contraseña_de_16_caracteres
export EMAIL_DESTINO=destino@empresa.cl
```

### Ejecutar

```bash
# Modo prueba (sin enviar correo)
python3 agente_uv.py --test

# Envío forzado de correo
python3 agente_uv.py --send

# Envío automático si las variables están configuradas
python3 agente_uv.py
```

## Estructura del proyecto

```
agente-uv-chile/
├── agente_uv.py              # Script principal
├── config.py                 # Configuración (ciudades, umbrales, etc.)
├── requirements.txt          # Dependencias Python
├── .env.example              # Ejemplo de variables de entorno
├── .gitignore                # Archivos ignorados por git
├── .github/
│   └── workflows/
│       └── agente_uv.yml     # Workflow de GitHub Actions
└── reportes/                 # Reportes generados (no se sube a git)
```

## Fuente de datos

- **API**: Open-Meteo (https://open-meteo.com/)
- **Licencia**: Gratuita, sin API key requerida
- **Datos**: Índice UV, temperatura máxima, código climático, probabilidad de precipitación

## Clasificación UV (OMS)

| Rango | Nivel | Color | Recomendación |
|-------|-------|-------|---------------|
| 0-2.99 | Bajo | Verde | Protección mínima |
| 3-5.99 | Moderado | Amarillo | SPF 30+, sombrero, gafas |
| 6-7.99 | Alto | Naranja | Reducir exposición 10-16h |
| 8-10.99 | Muy Alto | Rojo | Evitar exposición 10-16h, EPP obligatorio |
| 11+ | Extremo | Violeta | Suspender trabajo exterior 10-16h |

## Licencia

Uso interno.