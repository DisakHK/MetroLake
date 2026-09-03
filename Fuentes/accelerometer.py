"""Simulador de telemetria de vibracion."""

import math
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional

try:
    from .config import SENSORES_POR_TRAMO, TRAMOS
except ImportError:
    from config import SENSORES_POR_TRAMO, TRAMOS


class SimuladorAcelerometro:
    """Genera telemetria de vibracion para sensores IoT."""

    def __init__(self, tramos: Optional[List[Dict]] = None):
        self.tramos = tramos or TRAMOS
        self.sensores = self._crear_sensores()

    def _crear_sensores(self) -> List[Dict]:
        sensores = []
        for tramo in self.tramos:
            for posicion in range(SENSORES_POR_TRAMO):
                sensores.append({
                    "sensor_id": f"ACC-{tramo['id']}-{posicion + 1}",
                    "tramo_id": tramo["id"],
                    "origen": tramo["origen"],
                    "destino": tramo["destino"],
                    "posicion_m": round(tramo["longitud_m"] * (posicion + 1) / (SENSORES_POR_TRAMO + 1)),
                    "fatiga_base": tramo["fatiga_base"],
                    "antiguedad": tramo["antiguedad_anios"],
                    "offset_bias": round(random.gauss(0, 0.02), 4),
                })
        return sensores

    def _vibration_rms(self, sensor: Dict, ts: datetime, pasajeros: int = 300, precipitacion_mm: float = 0.0) -> float:
        hora = ts.hour + ts.minute / 60.0
        patron = 0.6 + 0.4 * (math.exp(-((hora - 7) ** 2) / 2) + math.exp(-((hora - 17.5) ** 2) / 2))
        base = 1.2 + sensor["fatiga_base"] * 2.5
        carga = 1.0 + (pasajeros / 1500) * 0.8
        lluvia = 1.0 + (precipitacion_mm / 50) * 0.3
        rms = base * patron * carga * lluvia + random.gauss(0, 0.15) + sensor["offset_bias"]
        return round(max(0.1, rms), 4)

    def generar_evento(self, sensor: Optional[Dict] = None, timestamp: Optional[datetime] = None,
                       pasajeros: Optional[int] = None, precipitacion_mm: Optional[float] = None) -> Dict:
        sensor = sensor or random.choice(self.sensores)
        ts = timestamp or datetime.now()
        pax = pasajeros if pasajeros is not None else random.randint(80, 1200)
        precip = precipitacion_mm if precipitacion_mm is not None else random.uniform(0, 30)
        rms = self._vibration_rms(sensor, ts, pax, precip)
        return {
            "event_id": f"VIB-{ts.strftime('%Y%m%d%H%M%S')}-{sensor['sensor_id']}",
            "sensor_id": sensor["sensor_id"], "tramo_id": sensor["tramo_id"],
            "estacion_origen": sensor["origen"], "estacion_destino": sensor["destino"],
            "posicion_m": sensor["posicion_m"], "timestamp": ts.isoformat(),
            "vibracion_rms_mm_s2": rms, "frecuencia_hz": round(random.uniform(5, 120), 2),
            "fatiga_acumulada": round(min(1.0, sensor["fatiga_base"] + rms * 0.02), 4),
            "es_anomalia": rms > 4.5 and sensor["fatiga_base"] > 0.5,
            "pasajeros_estimados": pax, "precipitacion_mm": round(precip, 2), "unidad": "mm/s²",
        }

    def generar_lote(self, n: int = 100, inicio: Optional[datetime] = None, intervalo_seg: int = 10) -> List[Dict]:
        inicio = inicio or datetime.now()
        return [self.generar_evento(sensor=self.sensores[i % len(self.sensores)],
                                    timestamp=inicio + timedelta(seconds=i * intervalo_seg))
                for i in range(n)]
