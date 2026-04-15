import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# =============================================================================
# Ciudades chilenas con coordenadas
# =============================================================================
CIUDADES = {
    "Iquique":      {"lat": -20.2133, "lon": -70.1503},
    "Chañaral":     {"lat": -26.3444, "lon": -70.6197},
    "Coquimbo":     {"lat": -29.9533, "lon": -71.3375},
    "Maipú":        {"lat": -33.5097, "lon": -70.7633},
    "Santiago":     {"lat": -33.4489, "lon": -70.6693},
    "Talcahuano":   {"lat": -36.7249, "lon": -73.1167},
    "Puerto Montt": {"lat": -41.4693, "lon": -72.9426},
    "Aysén":        {"lat": -45.4081, "lon": -72.3272},
}

# =============================================================================
# Umbrales de alerta
# =============================================================================
TEMP_ALERTA_CALOR = 33  # °C - Alerta de calor extremo
PRECIP_PROBAB_ALERTA = 70  # % - Probabilidad de precipitación para alerta

# =============================================================================
# Categorías UV (OMS) y recomendaciones SST
# =============================================================================
CATEGORIAS_UV = [
    {"min": 0,   "max": 2.99, "nivel": "Bajo",      "color": "#4CAF50",
     "recomendacion": (
         "Protección mínima requerida. Use gafas de sol en días brillantes. "
         "No se requiere EPP específico por radiación UV."
     )},
    {"min": 3,   "max": 5.99, "nivel": "Moderado",   "color": "#FFEB3B",
     "recomendacion": (
         "Use gafas de sol, sombrero de ala ancha y protector solar SPF 30+. "
         "Busque sombra durante las horas de mayor insolación (11:00-15:00). "
         "Trabajadores en exteriores: aplicar protector solar cada 2 horas."
     )},
    {"min": 6,   "max": 7.99, "nivel": "Alto",        "color": "#FF9800",
     "recomendacion": (
         "Reduzca la exposición solar entre 10:00-16:00. "
         "Protector solar SPF 30+ obligatorio, sombrero con ala ancha, gafas de sol. "
         "Rotar turnos de exposición cada 2 horas. "
         "Hidratación constante: mínimo 1 vaso de agua cada 30 minutos."
     )},
    {"min": 8,   "max": 10.99, "nivel": "Muy Alto",    "color": "#F44336",
     "recomendacion": (
         "ALERTA: Evite exposición solar entre 10:00-16:00. "
         "EPP obligatorio: sombrero con ala ancha, gafas UV400, protector SPF 50+, ropa manga larga. "
         "Implementar pausas de sombra cada 45 minutos. "
         "Hidratación obligatoria: 250 ml de agua cada 20 minutos. "
         "Supervisión activa de síntomas de golpe de calor."
     )},
    {"min": 11,  "max": 99,   "nivel": "Extremo",     "color": "#9C27B0",
     "recomendacion": (
         "ALERTA MÁXIMA: Suspender trabajo en exteriores entre 10:00-16:00. "
         "Protección total obligatoria: sombrero, gafas UV400, SPF 50+, ropa UV protectora. "
         "Si el trabajo exterior es imprescindible: turnos máximos de 30 minutos con pausas de 30 minutos en sombra. "
         "Hidratación forzada: 300 ml cada 15 minutos. "
         "Vigilar signos de agotamiento por calor: mareos, náuseas, confusión. "
         "Protocolo de emergencia térmico activo."
     )},
]

# =============================================================================
# Códigos WMO de clima (resumen de los más relevantes para alertas)
# =============================================================================
WEATHER_CODES = {
    0: "Despejado",
    1: "Mayormente despejado",
    2: "Parcialmente nublado",
    3: "Nublado",
    45: "Niebla",
    48: "Niebla con escarcha",
    51: "Llovizna ligera",
    53: "Llovizna moderada",
    55: "Llovizna intensa",
    61: "Lluvia ligera",
    63: "Lluvia moderada",
    65: "Lluvia intensa",
    71: "Nevada ligera",
    73: "Nevada moderada",
    75: "Nevada intensa",
    80: "Chubascos ligeros",
    81: "Chubascos moderados",
    82: "Chubascos fuertes",
    95: "Tormenta eléctrica",
    96: "Tormenta con granizo",
    99: "Tormenta con granizo fuerte",
}

# =============================================================================
# Configuración de correo
# =============================================================================
GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
EMAIL_DESTINO = os.environ.get("EMAIL_DESTINO", "robinson.armijo@esmax.cl")
EMAIL_ASUNTO = "Reporte Diario - Radiación UV y Alertas Climáticas | {fecha}"

# =============================================================================
# Configuración API MeteoChile (Dirección Meteorológica de Chile)
# =============================================================================
# Obtener credenciales en: https://climatologia.meteochile.gob.cl
# Registrarse → Iniciar Sesión → Obtener token de API
METEOCHILE_USER = os.environ.get("METEOCHILE_USER", "")
METEOCHILE_TOKEN = os.environ.get("METEOCHILE_TOKEN", "")

# Endpoints de las APIs de MeteoChile
METEOCHILE_UV_URL = (
    "https://climatologia.meteochile.gob.cl/application/servicios/getRecienteUvb"
)
METEOCHILE_EMA_URL = (
    "https://climatologia.meteochile.gob.cl/application/servicios/getEmaResumenDiario"
)
METEOCHILE_TIMEOUT = 30  # segundos

# =============================================================================
# Configuración API Open-Meteo (fallback)
# =============================================================================
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_PARAMS = [
    "uv_index_max",
    "temperature_2m_max",
    "weather_code",
    "precipitation_probability_max",
]
TIMEZONE = "America/Santiago"