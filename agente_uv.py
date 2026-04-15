#!/usr/bin/env python3
"""
Agente de Radiación UV y Alertas Climáticas para Chile
======================================================
Consulta diaria de índice UV, temperatura y condiciones climáticas
para ciudades chilenas. Genera recomendaciones SST/ESST y envía
reporte por correo electrónico.

Uso:
    python3 agente_uv.py              # Ejecución normal (envía correo)
    python3 agente_uv.py --test        # Modo prueba (muestra reporte sin enviar)
    python3 agente_uv.py --send        # Forzar envío de correo
"""

import sys
import os
import json
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, List, Dict

import requests

from config import (
    CIUDADES,
    CATEGORIAS_UV,
    TEMP_ALERTA_CALOR,
    PRECIP_PROBAB_ALERTA,
    WEATHER_CODES,
    GMAIL_USER,
    GMAIL_APP_PASSWORD,
    EMAIL_DESTINO,
    EMAIL_ASUNTO,
    OPEN_METEO_URL,
    OPEN_METEO_PARAMS,
    TIMEZONE,
)

from meteochile_api import (
    credenciales_disponibles,
    obtener_uv_meteochile,
    obtener_resumen_ema,
    encontrar_estacion_uv_cercana,
    encontrar_estacion_ema_cercana,
)


# =============================================================================
# Consulta de datos climáticos
# =============================================================================
def obtener_datos_open_meteo(ciudad: str, lat: float, lon: float) -> dict:
    """Consulta la API de Open-Meteo para obtener datos de UV y clima (fallback)."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ",".join(OPEN_METEO_PARAMS),
        "timezone": TIMEZONE,
        "forecast_days": 1,
    }

    try:
        response = requests.get(OPEN_METEO_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        daily = data.get("daily", {})
        return {
            "ciudad": ciudad,
            "uv_max": daily.get("uv_index_max", [None])[0],
            "temp_max": daily.get("temperature_2m_max", [None])[0],
            "weather_code": daily.get("weather_code", [None])[0],
            "precip_prob": daily.get("precipitation_probability_max", [None])[0],
            "fecha": daily.get("time", [""])[0],
            "fuente": "Open-Meteo",
            "estacion_uv": None,
            "estacion_ema": None,
            "error": None,
        }
    except requests.RequestException as e:
        return {
            "ciudad": ciudad,
            "uv_max": None,
            "temp_max": None,
            "weather_code": None,
            "precip_prob": None,
            "fecha": "",
            "fuente": "Sin datos",
            "estacion_uv": None,
            "estacion_ema": None,
            "error": str(e),
        }


def obtener_todos_los_datos() -> List[Dict]:
    """Obtiene datos climáticos para todas las ciudades.

    Estrategia:
      1. MeteoChile como fuente principal (UV + EMA)
      2. Open-Meteo como fallback para datos faltantes
    """
    resultados = []

    # ── Paso 1: Intentar obtener datos de MeteoChile ──
    estaciones_uv = None
    estaciones_ema = None

    if credenciales_disponibles():
        print("Consultando MeteoChile (DMC)...")
        estaciones_uv = obtener_uv_meteochile()
        estaciones_ema = obtener_resumen_ema()
    else:
        print("MeteoChile: Sin credenciales. Usando solo Open-Meteo.")

    # ── Paso 2: Para cada ciudad, buscar datos ──
    for ciudad, coords in CIUDADES.items():
        lat = coords["lat"]
        lon = coords["lon"]

        uv_meteochile = None
        temp_meteochile = None
        nombre_estacion_uv = None
        nombre_estacion_ema = None
        fuente_uv = "Open-Meteo"
        fuente_temp = "Open-Meteo"

        # Buscar estación UV cercana en MeteoChile
        if estaciones_uv:
            estacion_uv = encontrar_estacion_uv_cercana(lat, lon, estaciones_uv)
            if estacion_uv:
                uv_meteochile = estacion_uv["uv_max_hoy"]
                nombre_estacion_uv = estacion_uv["nombre_estacion"]
                fuente_uv = "MeteoChile DMC"

        # Buscar estación EMA cercana en MeteoChile
        if estaciones_ema:
            resultado_ema = encontrar_estacion_ema_cercana(lat, lon, estaciones_ema)
            if resultado_ema:
                codigo_ema, datos_ema = resultado_ema
                temp_meteochile = datos_ema.get("temp_max")
                nombre_estacion_ema = datos_ema.get("nombre")
                fuente_temp = "MeteoChile DMC"

        # Siempre consultar Open-Meteo para weather_code y precip
        # (MeteoChile no provee pronóstico de precipitación ni código WMO)
        datos_om = obtener_datos_open_meteo(ciudad, lat, lon)

        # Construir resultado combinando MeteoChile + Open-Meteo
        datos = {
            "ciudad": ciudad,
            "uv_max": uv_meteochile if uv_meteochile is not None else datos_om["uv_max"],
            "temp_max": temp_meteochile if temp_meteochile is not None else datos_om["temp_max"],
            "weather_code": datos_om["weather_code"],
            "precip_prob": datos_om["precip_prob"],
            "fecha": datos_om["fecha"],
            "fuente_uv": fuente_uv,
            "fuente_temp": fuente_temp,
            "estacion_uv": nombre_estacion_uv,
            "estacion_ema": nombre_estacion_ema,
            "error": datos_om["error"],
        }

        resultados.append(datos)

    return resultados


# =============================================================================
# Clasificación UV y recomendaciones SST
# =============================================================================
def clasificar_uv(uv_index: Optional[float]) -> Dict:
    """Retorna la categoría UV y recomendación SST según índice OMS."""
    if uv_index is None:
        return {
            "nivel": "Sin dato",
            "color": "#9E9E9E",
            "recomendacion": "No se pudo obtener el dato de radiación UV. Se recomienda precaución.",
        }

    for cat in CATEGORIAS_UV:
        if cat["min"] <= uv_index <= cat["max"]:
            return {
                "nivel": cat["nivel"],
                "color": cat["color"],
                "recomendacion": cat["recomendacion"],
            }

    return {
        "nivel": "Sin dato",
        "color": "#9E9E9E",
        "recomendacion": "No se pudo clasificar el índice UV.",
    }


# =============================================================================
# Detección de alertas
# =============================================================================
def detectar_alertas(datos: Dict) -> List[str]:
    """Detecta alertas climáticas basadas en umbrales configurados."""
    alertas = []

    if datos["temp_max"] is not None and datos["temp_max"] >= TEMP_ALERTA_CALOR:
        alertas.append(
            f"ALERTA CALOR EXTREMO: Temperatura máxima de {datos['temp_max']:.0f}°C "
            f"(umbral: {TEMP_ALERTA_CALOR}°C). "
            f"Implementar protocolo de calor: hidratación obligatoria cada 20 min, "
            f"pausas de sombra cada 45 min, supervisión activa de síntomas."
        )

    if datos["precip_prob"] is not None and datos["precip_prob"] >= PRECIP_PROBAB_ALERTA:
        alertas.append(
            f"ALERTA PRECIPITACIÓN: Probabilidad de lluvia del {datos['precip_prob']:.0f}%. "
            f"Evaluar condiciones de trabajo en exteriores. "
            f"Verificar calzado antideslizante y señalización de pisos mojados."
        )

    weather_code = datos["weather_code"]
    if weather_code is not None:
        # Tormentas eléctricas
        if weather_code >= 95:
            alertas.append(
                f"ALERTA TORMENTA ELÉCTRICA: {WEATHER_CODES.get(weather_code, 'Condición severa')}. "
                f"Suspender trabajo en altura y al aire libre. "
                f"Retirar equipos metálicos. Refugio en estructura segura."
            )
        # Lluvia intensa
        elif weather_code in (65, 82):
            alertas.append(
                f"ALERTA LLUVIA INTENSA: {WEATHER_CODES.get(weather_code, 'Precipitación fuerte')}. "
                f"Evaluar suspensión de actividades en exteriores. "
                f"Verificar drenaje en áreas de trabajo."
            )
        # Niebla
        elif weather_code in (45, 48):
            alertas.append(
                f"PRECAUCIÓN NIEBLA: Visibilidad reducida. "
                f"Usar elementos reflectantes. Reducir velocidad en vehículos."
            )

    if datos["uv_max"] is not None and datos["uv_max"] >= 11:
        alertas.append(
            f"ALERTA UV EXTREMO: Índice UV {datos['uv_max']:.1f}. "
            f"Suspender trabajo en exteriores entre 10:00-16:00. "
            f"Si es imprescindible, turnos máximos de 30 min con protección total."
        )

    return alertas


# =============================================================================
# Generación del reporte HTML
# =============================================================================
def generar_reporte_html(datos_ciudades: List[Dict]) -> str:
    """Genera el reporte HTML completo para enviar por correo."""
    hoy = datetime.now().strftime("%d/%m/%Y")
    hora = datetime.now().strftime("%H:%M")

    # Encabezado
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<style>
    body {{
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        color: #333;
        max-width: 900px;
        margin: 0 auto;
        padding: 20px;
        background-color: #f5f5f5;
    }}
    .header {{
        background: linear-gradient(135deg, #1a237e, #283593);
        color: white;
        padding: 25px 30px;
        border-radius: 10px 10px 0 0;
    }}
    .header h1 {{
        margin: 0;
        font-size: 22px;
    }}
    .header p {{
        margin: 5px 0 0 0;
        opacity: 0.9;
        font-size: 14px;
    }}
    .section {{
        background: white;
        padding: 20px 25px;
        margin: 0;
        border-bottom: 1px solid #eee;
    }}
    .section h2 {{
        color: #1a237e;
        margin: 0 0 15px 0;
        font-size: 18px;
        border-bottom: 2px solid #1a237e;
        padding-bottom: 8px;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
    }}
    th {{
        background-color: #1a237e;
        color: white;
        padding: 10px 8px;
        text-align: left;
        font-size: 13px;
    }}
    td {{
        padding: 10px 8px;
        border-bottom: 1px solid #e0e0e0;
    }}
    tr:nth-child(even) {{
        background-color: #f8f9fa;
    }}
    .uv-badge {{
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        color: white;
        font-weight: bold;
        font-size: 12px;
    }}
    .alert-box {{
        background: #fff3e0;
        border-left: 4px solid #ff9800;
        padding: 12px 15px;
        margin: 8px 0;
        border-radius: 4px;
        font-size: 13px;
    }}
    .alert-box.danger {{
        background: #ffebee;
        border-left-color: #f44336;
    }}
    .alert-box.extreme {{
        background: #fce4ec;
        border-left-color: #9c27b0;
    }}
    .rec-card {{
        background: #f8f9fa;
        border-radius: 6px;
        padding: 12px 15px;
        margin: 8px 0;
        border-left: 4px solid #ccc;
    }}
    .rec-card h4 {{
        margin: 0 0 5px 0;
        font-size: 14px;
    }}
    .rec-card p {{
        margin: 0;
        font-size: 13px;
        line-height: 1.5;
    }}
    .footer {{
        background: #e8eaf6;
        padding: 15px 25px;
        border-radius: 0 0 10px 10px;
        font-size: 12px;
        color: #666;
        text-align: center;
    }}
</style>
</head>
<body>
<div class="header">
    <h1>Reporte Diario: Radiación UV y Alertas Climáticas</h1>
    <p>Fecha: {hoy} | Generado a las: {hora} | Zona: Chile continental</p>
    <p style="font-size:12px;opacity:0.85;">Fuente principal: Dirección Meteorológica de Chile (MeteoChile) | Respaldo: Open-Meteo</p>
</div>
"""

    # ── Tabla resumen ──
    html += """
<div class="section">
    <h2>Resumen de Condiciones por Ciudad</h2>
    <table>
        <tr>
            <th>Ciudad</th>
            <th>UV Máx</th>
            <th>Nivel UV</th>
            <th>Temp. Máx</th>
            <th>Clima</th>
            <th>Precip. %</th>
            <th>Fuente UV</th>
        </tr>
"""

    for datos in datos_ciudades:
        uv = datos["uv_max"]
        temp = datos["temp_max"]
        cat = clasificar_uv(uv)
        clima = WEATHER_CODES.get(datos["weather_code"], "Sin dato")
        precip = f"{datos['precip_prob']:.0f}%" if datos["precip_prob"] is not None else "Sin dato"

        uv_display = f"{uv:.1f}" if uv is not None else "Sin dato"
        temp_display = f"{temp:.0f}°C" if temp is not None else "Sin dato"

        fuente_uv = datos.get("fuente_uv", "Open-Meteo")
        fuente_tag = "DMC" if "MeteoChile" in fuente_uv else "OM"
        fuente_color = "#1a237e" if "MeteoChile" in fuente_uv else "#757575"

        html += f"""        <tr>
            <td><strong>{datos['ciudad']}</strong></td>
            <td>{uv_display}</td>
            <td><span class="uv-badge" style="background-color:{cat['color']}">{cat['nivel']}</span></td>
            <td>{temp_display}</td>
            <td>{clima}</td>
            <td>{precip}</td>
            <td><span style="background:{fuente_color};color:white;padding:2px 6px;border-radius:8px;font-size:11px;">{fuente_tag}</span></td>
        </tr>
"""

    html += """    </table>
</div>
"""

    # ── Alertas ──
    todas_alertas = []
    for datos in datos_ciudades:
        alertas = detectar_alertas(datos)
        for alerta in alertas:
            todas_alertas.append((datos["ciudad"], alerta))

    if todas_alertas:
        html += """
<div class="section">
    <h2>Alertas Activas</h2>
"""
        for ciudad, alerta in todas_alertas:
            css_class = ""
            if "EXTREMO" in alerta or "TORMENTA" in alerta:
                css_class = "extreme"
            elif "CALOR" in alerta or "UV EXTREMO" in alerta:
                css_class = "danger"

            html += f"""    <div class="alert-box {css_class}">
        <strong>{ciudad}:</strong> {alerta}
    </div>
"""
        html += """</div>
"""

    # ── Recomendaciones SST por ciudad ──
    html += """
<div class="section">
    <h2>Recomendaciones SST por Ciudad</h2>
"""

    for datos in datos_ciudades:
        cat = clasificar_uv(datos["uv_max"])
        html += f"""    <div class="rec-card" style="border-left-color:{cat['color']}">
        <h4>{datos['ciudad']} - UV {cat['nivel']}</h4>
        <p>{cat['recomendacion']}</p>
    </div>
"""

    html += """</div>
"""

    # ── Pie de página ──
    html += f"""
<div class="footer">
    <p>Reporte generado automáticamente | Fuente primaria: <strong>Dirección Meteorológica de Chile (DMC)</strong> | Respaldo: Open-Meteo API | Clasificación UV: OMS</p>
    <p><strong>DMC</strong> = MeteoChile (datos oficiales) | <strong>OM</strong> = Open-Meteo (pronóstico)</p>
    <p>Este reporte es informativo. En caso de condiciones extremas, siga los protocolos de emergencia de su empresa.</p>
</div>
</body>
</html>"""

    return html


def generar_reporte_texto(datos_ciudades: List[Dict]) -> str:
    """Genera versión texto plano del reporte (resumen rápido para Teams)."""
    hoy = datetime.now().strftime("%d/%m/%Y")
    lineas = [
        f"REPORTE DIARIO UV Y CLIMA - {hoy}",
        "=" * 50,
        "",
    ]

    for datos in datos_ciudades:
        uv = datos["uv_max"]
        cat = clasificar_uv(uv)
        temp = datos["temp_max"]
        clima = WEATHER_CODES.get(datos["weather_code"], "Sin dato")

        uv_display = f"{uv:.1f}" if uv is not None else "N/D"
        temp_display = f"{temp:.0f}°C" if temp is not None else "N/D"

        lineas.append(f"• {datos['ciudad']}: UV {uv_display} ({cat['nivel']}) | Temp: {temp_display} | {clima}")

    # Alertas
    todas_alertas = []
    for datos in datos_ciudades:
        alertas = detectar_alertas(datos)
        for alerta in alertas:
            todas_alertas.append((datos["ciudad"], alerta))

    if todas_alertas:
        lineas.append("")
        lineas.append("ALERTAS:")
        lineas.append("-" * 50)
        for ciudad, alerta in todas_alertas:
            lineas.append(f"⚠ {ciudad}: {alerta}")

    lineas.append("")
    lineas.append("RECOMENDACIONES SST:")
    lineas.append("-" * 50)
    for datos in datos_ciudades:
        cat = clasificar_uv(datos["uv_max"])
        lineas.append(f"• {datos['ciudad']} ({cat['nivel']}): {cat['recomendacion']}")

    lineas.append("")
    lineas.append("Reporte generado automáticamente | Fuente primaria: MeteoChile DMC | Respaldo: Open-Meteo | Clasificación UV: OMS")

    return "\n".join(lineas)


# =============================================================================
# Envío de correo electrónico
# =============================================================================
def enviar_correo(html_content: str, texto_content: str) -> bool:
    """Envía el reporte por correo electrónico vía Gmail SMTP."""
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print("ERROR: Configurar GMAIL_USER y GMAIL_APP_PASSWORD en las variables de entorno.")
        print("  export GMAIL_USER=tu_correo@gmail.com")
        print("  export GMAIL_APP_PASSWORD=tu_contraseña_de_aplicacion")
        return False

    hoy = datetime.now().strftime("%d/%m/%Y")
    asunto = EMAIL_ASUNTO.format(fecha=hoy)

    msg = MIMEMultipart("alternative")
    msg["From"] = GMAIL_USER
    msg["To"] = EMAIL_DESTINO
    msg["Subject"] = asunto

    part_text = MIMEText(texto_content, "plain", "utf-8")
    part_html = MIMEText(html_content, "html", "utf-8")

    msg.attach(part_text)
    msg.attach(part_html)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, EMAIL_DESTINO, msg.as_string())
        print(f"Correo enviado exitosamente a {EMAIL_DESTINO}")
        return True
    except smtplib.SMTPAuthenticationError:
        print("ERROR: Autenticación fallida. Verifique GMAIL_USER y GMAIL_APP_PASSWORD.")
        print("  Asegúrese de usar una 'Contraseña de aplicación' de Google, no su contraseña normal.")
        return False
    except Exception as e:
        print(f"ERROR al enviar correo: {e}")
        return False


# =============================================================================
# Main
# =============================================================================
def main():
    modo_test = "--test" in sys.argv
    modo_send = "--send" in sys.argv

    print("=" * 60)
    print("Agente UV y Alertas Climáticas - Chile")
    print("=" * 60)
    print(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"Ciudades: {', '.join(CIUDADES.keys())}")
    if credenciales_disponibles():
        print(f"Fuente principal: MeteoChile DMC (Dirección Meteorológica de Chile)")
        print(f"Fallback: Open-Meteo API")
    else:
        print(f"Fuente: Open-Meteo API (MeteoChile sin credenciales)")
    print()

    # Obtener datos climáticos
    print("Obteniendo datos climáticos...")
    datos = obtener_todos_los_datos()

    # Mostrar resumen en consola
    print("\nResumen:")
    print("-" * 60)
    for d in datos:
        if d["error"]:
            print(f"  {d['ciudad']}: ERROR - {d['error']}")
            continue

        uv = d["uv_max"]
        cat = clasificar_uv(uv)
        temp = d["temp_max"]
        clima = WEATHER_CODES.get(d["weather_code"], "Sin dato")
        fuente = d.get("fuente_uv", "Open-Meteo")
        fuente_short = "DMC" if "MeteoChile" in fuente else "OM"

        uv_display = f"{uv:.1f}" if uv is not None else "N/D"
        temp_display = f"{temp:.0f}°C" if temp is not None else "N/D"

        print(f"  {d['ciudad']:15s} | UV: {uv_display:5s} ({cat['nivel']:10s}) | {temp_display:6s} | {clima} [{fuente_short}]")

        alertas = detectar_alertas(d)
        for alerta in alertas:
            print(f"    ALERTA: {alerta}")

    # Generar reportes
    print("\nGenerando reporte...")
    html_content = generar_reporte_html(datos)
    texto_content = generar_reporte_texto(datos)

    # Guardar reportes localmente como respaldo
    report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reportes")
    os.makedirs(report_dir, exist_ok=True)

    fecha_archivo = datetime.now().strftime("%Y-%m-%d")
    html_path = os.path.join(report_dir, f"reporte_uv_{fecha_archivo}.html")
    txt_path = os.path.join(report_dir, f"reporte_uv_{fecha_archivo}.txt")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Reporte HTML guardado: {html_path}")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(texto_content)
    print(f"Reporte TXT guardado: {txt_path}")

    # Envío de correo
    if modo_test:
        print("\nModo TEST: No se envía correo. Los reportes se guardaron localmente.")
        print("Para enviar correo, ejecute sin --test o con --send.")
    elif modo_send or (GMAIL_USER and GMAIL_APP_PASSWORD):
        print("\nEnviando correo...")
        enviar_correo(html_content, texto_content)
    else:
        print("\nNo se configuró correo. Los reportes se guardaron localmente.")
        print("Para enviar por correo, configure las variables de entorno:")
        print("  export GMAIL_USER=tu_correo@gmail.com")
        print("  export GMAIL_APP_PASSWORD=tu_contraseña_de_aplicacion")

    print("\nListo!")


if __name__ == "__main__":
    main()