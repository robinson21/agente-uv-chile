#!/usr/bin/env python3
"""
Servidor API local para el Agente UV
====================================
Proporciona un endpoint HTTP para que el frontend obtenga datos climáticos.

Uso:
    python3 api_server.py [--port 8000]
"""

import json
import argparse
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import os
import sys

# Agregar ruta al directorio actual para imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import CIUDADES, WEATHER_CODES
from meteochile_api import (
    credenciales_disponibles,
    obtener_uv_meteochile,
    obtener_resumen_ema,
    encontrar_estacion_uv_cercana,
    encontrar_estacion_ema_cercana,
)


def obtener_datos_ciudad(ciudad: str, lat: float, lon: float) -> dict:
    """Obtiene datos climáticos para una ciudad específica."""
    resultado = {
        "ciudad": ciudad,
        "lat": lat,
        "lon": lon,
        "uv": 0,
        "temperatura": 0,
        "clima": 0,
        "precipitacion": 0,
        "humedad": None,
        "fuente": "Sin datos"
    }

    # Intentar primero con MeteoChile si hay credenciales
    if credenciales_disponibles():
        # Datos UV
        estaciones_uv = obtener_uv_meteochile()
        if estaciones_uv:
            estacion = encontrar_estacion_uv_cercana(lat, lon, estaciones_uv)
            if estacion:
                resultado["uv"] = estacion.get("uv_max_hoy", 0)
                resultado["fuente"] = "MeteoChile"

        # Datos EMA (temperatura, humedad, etc.)
        estaciones_ema = obtener_resumen_ema()
        if estaciones_ema:
            ema = encontrar_estacion_ema_cercana(lat, lon, estaciones_ema)
            if ema:
                _, datos = ema
                if resultado["fuente"] == "MeteoChile":
                    resultado["fuente"] = "MeteoChile"
                resultado["temperatura"] = datos.get("temp_max") or datos.get("temp_min") or 0
                resultado["humedad"] = datos.get("humedad")
                resultado["precipitacion"] = 0  # MeteoChile no da probabilidad, da acumulado

    # Si no hay datos de MeteoChile, usar Open-Meteo como fallback
    if resultado["fuente"] == "Sin datos":
        try:
            import requests
            params = {
                "latitude": lat,
                "longitude": lon,
                "daily": "uv_index_max,temperature_2m_max,weather_code,precipitation_probability_max",
                "timezone": "America/Santiago",
                "forecast_days": 1
            }
            response = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params=params,
                timeout=10
            )
            if response.ok:
                data = response.json()
                daily = data.get("daily", {})
                resultado["uv"] = daily.get("uv_index_max", [0])[0]
                resultado["temperatura"] = daily.get("temperature_2m_max", [0])[0]
                resultado["clima"] = daily.get("weather_code", [0])[0]
                resultado["precipitacion"] = daily.get("precipitation_probability_max", [0])[0]
                resultado["fuente"] = "Open-Meteo"
        except Exception as e:
            print(f"Error Open-Meteo: {e}")

    return resultado


def obtener_todos_los_datos() -> dict:
    """Obtiene datos para todas las ciudades."""
    resultados = {}
    for ciudad, coords in CIUDADES.items():
        resultados[ciudad] = obtener_datos_ciudad(
            ciudad,
            coords["lat"],
            coords["lon"]
        )
    return resultados


class AgenteUVHandler(SimpleHTTPRequestHandler):
    """Handler HTTP con soporte CORS y endpoints API."""

    def do_OPTIONS(self):
        """Manejar preflight CORS."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        """Manejar requests GET."""
        parsed_path = urlparse(self.path)

        # Endpoint API: /api/datos
        if parsed_path.path == '/api/datos':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            datos = obtener_todos_los_datos()
            response = {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "data": datos
            }
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode())
            return

        # Endpoint API: /api/health
        if parsed_path.path == '/api/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            response = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "meteochile_configured": credenciales_disponibles()
            }
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode())
            return

        # Servir archivos estáticos del frontend
        if parsed_path.path == '/' or parsed_path.path == '/index.html':
            self.path = '/frontend/index.html'
        elif parsed_path.path.startswith('/frontend'):
            pass  # Ya apunta al directorio correcto
        else:
            # Intentar servir desde frontend
            self.path = f'/frontend{parsed_path.path}'

        return super().do_GET()

    def log_message(self, format, *args):
        """Log personalizado."""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")


def main():
    parser = argparse.ArgumentParser(description='Servidor API Agente UV')
    parser.add_argument('--port', '-p', type=int, default=8000,
                        help='Puerto del servidor (default: 8000)')
    parser.add_argument('--host', '-H', type=str, default='0.0.0.0',
                        help='Host del servidor (default: 0.0.0.0)')
    args = parser.parse_args()

    server_address = (args.host, args.port)
    httpd = HTTPServer(server_address, AgenteUVHandler)

    print("=" * 60)
    print("Servidor API Agente UV")
    print("=" * 60)
    print(f"Puerto: {args.port}")
    print(f"Host: {args.host}")
    print("-" * 60)
    print("Endpoints disponibles:")
    print(f"  http://localhost:{args.port}/              - Frontend")
    print(f"  http://localhost:{args.port}/api/datos     - Datos climáticos")
    print(f"  http://localhost:{args.port}/api/health    - Estado del servidor")
    print("-" * 60)
    print(f"MeteoChile configurado: {'Sí' if credenciales_disponibles() else 'No'}")
    print("=" * 60)
    print("Presione Ctrl+C para detener el servidor")
    print()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
        httpd.shutdown()


if __name__ == '__main__':
    main()
