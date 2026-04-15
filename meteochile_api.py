#!/usr/bin/env python3
"""
Módulo de consulta a las APIs oficiales de MeteoChile (DMC)
============================================================
Consulta datos de radiación UV y resumen diario de estaciones
automáticas (EMA) desde la Dirección Meteorológica de Chile.

APIs utilizadas:
  - getRecienteUvb: Índice UV cada 5 min, red nacional (últimos 5 días)
  - getEmaResumenDiario: Resumen diario de estaciones automáticas

Requiere credenciales: usuario (correo) + token (API key personal).
Obtener en: https://climatologia.meteochile.gob.cl
"""

import math
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Tuple

import requests

from config import (
    METEOCHILE_USER,
    METEOCHILE_TOKEN,
    METEOCHILE_UV_URL,
    METEOCHILE_EMA_URL,
    METEOCHILE_TIMEOUT,
)


# =============================================================================
# Utilidades
# =============================================================================
def _distancia_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula la distancia en km entre dos coordenadas usando Haversine."""
    R = 6371  # Radio de la Tierra en km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def credenciales_disponibles() -> bool:
    """Verifica si las credenciales de MeteoChile están configuradas."""
    return bool(METEOCHILE_USER) and bool(METEOCHILE_TOKEN)


# =============================================================================
# Consulta de datos UV desde MeteoChile
# =============================================================================
def obtener_uv_meteochile() -> Optional[List[Dict]]:
    """
    Consulta la API getRecienteUvb de MeteoChile.

    Retorna una lista de diccionarios con el UV máximo del día actual
    por cada estación de monitoreo UV. Cada dict contiene:
        - nombre_estacion: str
        - codigo_nacional: int
        - latitud: float
        - longitud: float
        - uv_max_hoy: float (máximo UV del día actual)
        - hora_max: str (hora del máximo UV)

    Retorna None si la consulta falla.
    """
    if not credenciales_disponibles():
        print("  MeteoChile: Sin credenciales configuradas.")
        return None

    params = {"usuario": METEOCHILE_USER, "token": METEOCHILE_TOKEN}

    try:
        response = requests.get(
            METEOCHILE_UV_URL, params=params, timeout=METEOCHILE_TIMEOUT, verify=True
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        print(f"  MeteoChile UV: Error de conexión - {e}")
        return None
    except ValueError as e:
        print(f"  MeteoChile UV: Error parseando JSON - {e}")
        return None

    # Obtener fecha de hoy en zona horaria de Chile (UTC-3 o UTC-4)
    # Los datos vienen en UTC, usamos la fecha del reporte
    hoy_str = datetime.now().strftime("%d-%m-%Y")

    estaciones_uv = []
    datos_recientes = data.get("datosRecientes", [])

    for estacion_data in datos_recientes:
        estacion_info = estacion_data.get("estacion", {})
        indices_uv = estacion_data.get("indiceUV", [])

        if not indices_uv:
            continue

        # Filtrar mediciones del día actual y encontrar el máximo
        uv_max = 0.0
        hora_max = ""

        for medicion in indices_uv:
            fecha = medicion.get("fecha", "")
            uv_valor = medicion.get("indiceUV", "0")

            if fecha == hoy_str:
                try:
                    uv_float = float(uv_valor)
                    if uv_float > uv_max:
                        uv_max = uv_float
                        hora_max = medicion.get("hora", "")
                except (ValueError, TypeError):
                    continue

        # Si no hay datos de hoy, usar el último día disponible
        if uv_max == 0.0 and indices_uv:
            # Tomar la fecha más reciente
            fechas = set(m.get("fecha", "") for m in indices_uv if m.get("fecha"))
            if fechas:
                fecha_reciente = sorted(fechas, key=lambda x: datetime.strptime(x, "%d-%m-%Y"), reverse=True)[0]
                for medicion in indices_uv:
                    if medicion.get("fecha") == fecha_reciente:
                        try:
                            uv_float = float(medicion.get("indiceUV", "0"))
                            if uv_float > uv_max:
                                uv_max = uv_float
                                hora_max = medicion.get("hora", "")
                        except (ValueError, TypeError):
                            continue

        estaciones_uv.append({
            "nombre_estacion": estacion_info.get("nombreEstacion", "").strip(),
            "codigo_nacional": estacion_info.get("codigoNacional"),
            "latitud": estacion_info.get("latitud"),
            "longitud": estacion_info.get("longitud"),
            "uv_max_hoy": uv_max,
            "hora_max": hora_max,
        })

    if estaciones_uv:
        print(f"  MeteoChile UV: {len(estaciones_uv)} estaciones con datos.")
    else:
        print("  MeteoChile UV: Sin datos de estaciones.")

    return estaciones_uv if estaciones_uv else None


# =============================================================================
# Consulta de resumen diario EMA desde MeteoChile
# =============================================================================
def obtener_resumen_ema() -> Optional[Dict]:
    """
    Consulta la API getEmaResumenDiario de MeteoChile.

    Retorna un diccionario con código de estación como clave y datos como valor:
        {
            "180005": {
                "nombre": str,
                "latitud": float,
                "longitud": float,
                "temp_max": float,
                "temp_min": float,
                "precipitacion": float,
                "humedad": float,
                "viento_max": float,
            },
            ...
        }

    Retorna None si la consulta falla.
    """
    if not credenciales_disponibles():
        return None

    params = {"usuario": METEOCHILE_USER, "token": METEOCHILE_TOKEN}

    try:
        response = requests.get(
            METEOCHILE_EMA_URL, params=params, timeout=METEOCHILE_TIMEOUT, verify=True
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        print(f"  MeteoChile EMA: Error de conexión - {e}")
        return None
    except ValueError as e:
        print(f"  MeteoChile EMA: Error parseando JSON - {e}")
        return None

    estaciones = data.get("estaciones", {})
    resultado = {}

    for codigo, info in estaciones.items():
        datos_estacion = info.get("datosEstacion", {})
        datos_resumen = info.get("datosResumenEma", {})

        if not datos_resumen.get("conDatos", False):
            continue

        datos = datos_resumen.get("datos", {})
        valores_recientes = datos.get("valoresMasRecientes", {})
        temp_extremas = datos.get("temperaturaExtremas", {})

        # Obtener temperatura máxima y mínima del día más reciente
        temp_max = None
        temp_min = None

        if temp_extremas:
            # Las fechas vienen como claves "dd-mm-aaaa"
            fechas = sorted(temp_extremas.keys(), reverse=True)
            if fechas:
                dia_reciente = temp_extremas[fechas[0]]
                try:
                    maxima = dia_reciente.get("maxima", {})
                    minima = dia_reciente.get("minima", {})
                    temp_max = float(maxima.get("valor")) if maxima.get("valor") else None
                    temp_min = float(minima.get("valor")) if minima.get("valor") else None
                except (ValueError, TypeError):
                    pass

        # Precipitación del día
        precip = 0.0
        agua_diaria = datos.get("aguaCaidaDiaria", {})
        if agua_diaria:
            fechas_agua = sorted(agua_diaria.keys(), reverse=True)
            if fechas_agua:
                try:
                    precip = float(agua_diaria[fechas_agua[0]].get("valor", 0))
                except (ValueError, TypeError):
                    precip = 0.0

        # Humedad y viento recientes
        humedad = None
        viento_max = None
        try:
            humedad = float(valores_recientes.get("humedadRelativa")) if valores_recientes.get("humedadRelativa") else None
        except (ValueError, TypeError):
            pass

        # Viento máximo del día
        viento_data = datos.get("vientoMaxino", {})
        if viento_data:
            fechas_viento = sorted(viento_data.keys(), reverse=True)
            if fechas_viento:
                try:
                    viento_max = float(
                        viento_data[fechas_viento[0]].get("maxima", {}).get("intensidad", 0)
                    )
                except (ValueError, TypeError):
                    viento_max = None

        lat = datos_estacion.get("latitud")
        lon = datos_estacion.get("longitud")
        try:
            lat = float(lat) if lat else None
            lon = float(lon) if lon else None
        except (ValueError, TypeError):
            lat = None
            lon = None

        resultado[codigo] = {
            "nombre": datos_estacion.get("nombreEstacion", "").strip(),
            "latitud": lat,
            "longitud": lon,
            "region": datos_estacion.get("region", ""),
            "temp_max": temp_max,
            "temp_min": temp_min,
            "precipitacion": precip,
            "humedad": humedad,
            "viento_max": viento_max,
        }

    if resultado:
        print(f"  MeteoChile EMA: {len(resultado)} estaciones con datos.")
    else:
        print("  MeteoChile EMA: Sin datos de estaciones.")

    return resultado if resultado else None


# =============================================================================
# Búsqueda de estación cercana
# =============================================================================
def encontrar_estacion_uv_cercana(
    lat: float, lon: float, estaciones_uv: List[Dict], max_distancia_km: float = 100.0
) -> Optional[Dict]:
    """
    Encuentra la estación UV de MeteoChile más cercana a las coordenadas dadas.

    Args:
        lat: Latitud de la ciudad
        lon: Longitud de la ciudad
        estaciones_uv: Lista de estaciones UV de MeteoChile
        max_distancia_km: Distancia máxima aceptable (default: 100 km)

    Returns:
        Dict con datos de la estación más cercana, o None si ninguna está dentro del rango.
    """
    mejor = None
    mejor_dist = float("inf")

    for estacion in estaciones_uv:
        est_lat = estacion.get("latitud")
        est_lon = estacion.get("longitud")

        if est_lat is None or est_lon is None:
            continue

        dist = _distancia_haversine(lat, lon, est_lat, est_lon)
        if dist < mejor_dist:
            mejor_dist = dist
            mejor = estacion

    if mejor and mejor_dist <= max_distancia_km:
        mejor["distancia_km"] = round(mejor_dist, 1)
        return mejor

    return None


def encontrar_estacion_ema_cercana(
    lat: float, lon: float, estaciones_ema: Dict, max_distancia_km: float = 80.0
) -> Optional[Tuple[str, Dict]]:
    """
    Encuentra la estación EMA de MeteoChile más cercana a las coordenadas dadas.

    Args:
        lat: Latitud de la ciudad
        lon: Longitud de la ciudad
        estaciones_ema: Dict de estaciones EMA de MeteoChile
        max_distancia_km: Distancia máxima aceptable (default: 80 km)

    Returns:
        Tupla (codigo, datos) de la estación más cercana, o None.
    """
    mejor_codigo = None
    mejor_datos = None
    mejor_dist = float("inf")

    for codigo, datos in estaciones_ema.items():
        est_lat = datos.get("latitud")
        est_lon = datos.get("longitud")

        if est_lat is None or est_lon is None:
            continue

        dist = _distancia_haversine(lat, lon, est_lat, est_lon)
        if dist < mejor_dist:
            mejor_dist = dist
            mejor_codigo = codigo
            mejor_datos = datos

    if mejor_codigo and mejor_dist <= max_distancia_km:
        mejor_datos["distancia_km"] = round(mejor_dist, 1)
        return (mejor_codigo, mejor_datos)

    return None
