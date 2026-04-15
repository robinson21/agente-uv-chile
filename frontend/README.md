# Frontend Agente UV - Chile

Aplicación web React para visualizar los datos de radiación UV y condiciones climáticas de Chile.

## Características

- **Detección automática de conexión**: Detecta si hay conexión a internet
- **API Local**: Se conecta automáticamente al servidor local para usar datos de MeteoChile
- **Modo fallback**: Usa Open-Meteo directamente si no hay API local disponible
- **Interfaz moderna**: Diseño responsivo con tarjetas por ciudad
- **Alertas climáticas**: Notificaciones visuales para precipitaciones altas
- **Recomendaciones SST**: Indicaciones según nivel UV

## Uso

### Opción 1: Servidor Python (Recomendado)

Inicia el servidor API local que proporciona datos desde MeteoChile:

```bash
cd "/Users/robinsonarmijovargas/Desktop/Agente Clima"
python3 api_server.py --port 8000
```

Luego abre en tu navegador:
- **Frontend**: http://localhost:8000
- **API Datos**: http://localhost:8000/api/datos
- **API Health**: http://localhost:8000/api/health

### Opción 2: Abrir HTML directamente

Puedes abrir el archivo `index.html` directamente en tu navegador:

```bash
open frontend/index.html
```

En este modo:
- Si el servidor local está corriendo, se conectará automáticamente
- Si no, usará Open-Meteo directamente desde el navegador (requiere internet)

## Estructura de archivos

```
frontend/
├── index.html          # Aplicación React completa (autocontenida)
└── README.md           # Este archivo
```

## Modos de operación

| Modo | Descripción | Requiere |
|------|-------------|----------|
| **Auto-detectar** | Detecta automáticamente si hay API local | Ambos |
| **API Local** | Usa el servidor Python (MeteoChile) | Servidor corriendo |
| **Directo** | Usa Open-Meteo desde el navegador | Internet |

## Endpoints de la API

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` | GET | Sirve el frontend |
| `/api/datos` | GET | Datos climáticos de todas las ciudades |
| `/api/health` | GET | Estado del servidor |

### Respuesta de `/api/datos`

```json
{
  "success": true,
  "timestamp": "2026-04-14T23:10:44.878927",
  "data": {
    "Santiago": {
      "ciudad": "Santiago",
      "uv": 4.0,
      "temperatura": 18.5,
      "clima": 0,
      "precipitacion": 10,
      "humedad": 45,
      "fuente": "MeteoChile"
    }
  }
}
```

## Tecnologías

- **React 18** (desde CDN)
- **Babel Standalone** (para JSX en el navegador)
- **CSS3** con gradientes y animaciones
- **Fetch API** para requests HTTP

## Requisitos

- Python 3.7+ (para el servidor API)
- Navegador moderno (Chrome, Firefox, Safari, Edge)
