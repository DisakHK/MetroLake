"""Logica del clima: API Open-Meteo con fallback a datos simulados."""

import math
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests


class SimuladorClima:
    """Obtiene lluvia de Open-Meteo o la simula si la API no esta disponible."""

    PLUVIOMETROS = [
        {"id": "PLV-001", "nombre": "Estacion Olaya Herrera", "lat": 6.2204, "lon": -75.5900},
        {"id": "PLV-002", "nombre": "Estacion Bello", "lat": 6.3356, "lon": -75.5596},
        {"id": "PLV-003", "nombre": "Estacion Itagui", "lat": 6.1844, "lon": -75.5992},
        {"id": "PLV-004", "nombre": "Estacion Envigado", "lat": 6.1714, "lon": -75.5773},
        {"id": "PLV-005", "nombre": "Estacion Sabaneta", "lat": 6.1517, "lon": -75.6167},
        {"id": "PLV-006", "nombre": "Estacion Caldas", "lat": 6.0893, "lon": -75.6364},
        {"id": "PLV-007", "nombre": "Estacion La Estrella", "lat": 6.1583, "lon": -75.6428},
    ]
    NIVELES_ALERTA = [
        {"nivel": "verde", "min_mm": 0}, {"nivel": "amarilla", "min_mm": 10},
        {"nivel": "naranja", "min_mm": 30}, {"nivel": "roja", "min_mm": 60},
    ]

    def __init__(self):
        self.cache_api = {}
        self.ultima_llamada_api = None

    def _patron_estacional(self, ts: datetime) -> float:
        if ts.month in [4, 5, 10, 11]:
            return random.uniform(0.6, 1.0)
        if ts.month in [3, 6, 9]:
            return random.uniform(0.3, 0.6)
        return random.uniform(0.05, 0.3)

    def _nivel_alerta(self, precipitacion_mm: float) -> str:
        for nivel in reversed(self.NIVELES_ALERTA):
            if precipitacion_mm >= nivel["min_mm"]:
                return nivel["nivel"]
        return "verde"

    @staticmethod
    def _grados_a_cardinal(grados: float) -> str:
        direcciones = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]
        return direcciones[int(grados / 45 + 0.5) % 8]

    def _intentar_api(self) -> bool:
        ahora = datetime.now()
        if self.ultima_llamada_api and (ahora - self.ultima_llamada_api).total_seconds() < 300:
            return bool(self.cache_api)
        params = {
            "latitude": ",".join(str(p["lat"]) for p in self.PLUVIOMETROS),
            "longitude": ",".join(str(p["lon"]) for p in self.PLUVIOMETROS),
            "current": ["temperature_2m", "relative_humidity_2m", "precipitation", "wind_speed_10m", "wind_direction_10m"],
            "daily": ["precipitation_sum"], "timezone": "America/Bogota",
        }
        try:
            response = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=5)
            response.raise_for_status()
            datos_api = response.json()
        except requests.exceptions.RequestException:
            return False
        if not isinstance(datos_api, list):
            return False
        for pluv, estacion in zip(self.PLUVIOMETROS, datos_api):
            current = estacion.get("current", {})
            daily = estacion.get("daily", {})
            precipitacion_diaria = daily.get("precipitation_sum") or [0.0]
            self.cache_api[pluv["id"]] = {
                "precipitacion": current.get("precipitation", 0.0),
                "precip_acumulada": precipitacion_diaria[0],
                "humedad": current.get("relative_humidity_2m", 0),
                "temperatura": current.get("temperature_2m", 0.0),
                "vel_viento": current.get("wind_speed_10m", 0.0),
                "dir_viento": self._grados_a_cardinal(current.get("wind_direction_10m", 0)),
            }
        self.ultima_llamada_api = ahora
        return True

    def _generar_fallback(self, ts: datetime) -> Dict:
        estacional = self._patron_estacional(ts)
        factor_hora = 1.0 + 0.8 * math.exp(-((ts.hour - 16) ** 2) / 8)
        esta_lloviendo = random.random() < estacional * 0.6
        precipitacion = round(
            min(120, random.expovariate(1 / (15 * estacional * factor_hora)))
            if esta_lloviendo else random.uniform(0, 0.5),
            2,
        )
        return {
            "precipitacion": precipitacion,
            "precip_acumulada": round(precipitacion * random.uniform(1, 8), 2),
            "humedad": round(min(100, 60 + precipitacion * 0.5 + random.gauss(0, 5)), 1),
            "temperatura": round(random.gauss(22, 3) - precipitacion * 0.05, 1),
            "vel_viento": round(random.gauss(12, 5), 1),
            "dir_viento": random.choice(["N", "NE", "E", "SE", "S", "SO", "O", "NO"]),
        }

    def generar_lectura(self, pluviometro: Optional[Dict] = None, timestamp: Optional[datetime] = None) -> Dict:
        pluv = pluviometro or random.choice(self.PLUVIOMETROS)
        ts = timestamp or datetime.now()
        es_actual = abs((datetime.now() - ts).total_seconds()) < 7200
        datos = None
        if es_actual and self._intentar_api():
            datos = self.cache_api.get(pluv["id"])
        if datos is None:
            datos = self._generar_fallback(ts)
        precipitacion = datos["precipitacion"]
        precip_acumulada = datos["precip_acumulada"]
        humedad, temperatura = datos["humedad"], datos["temperatura"]
        vel_viento, dir_viento = datos["vel_viento"], datos["dir_viento"]
        esta_lloviendo = precipitacion > 0.0
        return {
            "lectura_id": f"CLIMA-{ts.strftime('%Y%m%d%H%M')}-{pluv['id']}", "pluviometro_id": pluv["id"],
            "nombre_estacion": pluv["nombre"], "latitud": pluv["lat"], "longitud": pluv["lon"], "timestamp": ts.isoformat(),
            "precipitacion_mm_h": precipitacion, "precipitacion_acumulada_dia_mm": precip_acumulada,
            "humedad_relativa_pct": humedad, "temperatura_c": temperatura, "nivel_alerta": self._nivel_alerta(precipitacion),
            "esta_lloviendo": esta_lloviendo, "velocidad_viento_km_h": vel_viento, "direccion_viento": dir_viento,
            "visibilidad_km": round(max(0.5, 10 - precipitacion * 0.1 + random.gauss(0, 1)), 1),
        }

    def generar_lote(self, n_lecturas: int = 50, inicio: Optional[datetime] = None, intervalo_min: int = 5) -> List[Dict]:
        inicio = inicio or datetime.now()
        return [self.generar_lectura(pluviometro=pluv, timestamp=inicio + timedelta(minutes=i * intervalo_min))
                for i in range(n_lecturas) for pluv in self.PLUVIOMETROS]


__all__ = ["SimuladorClima"]
