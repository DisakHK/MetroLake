"""Simulador de eventos de torniquetes y pasajeros."""

import math
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional

try:
    from .config import ESTACIONES
except ImportError:
    from config import ESTACIONES


class SimuladorTorniquetes:
    CAPACIDAD_TREN = 1500

    def __init__(self, estaciones: Optional[List[str]] = None):
        self.estaciones = estaciones or ESTACIONES
        self.perfiles = self._crear_perfiles()

    def _crear_perfiles(self) -> Dict[str, Dict]:
        perfiles = {}
        centrales = {"San Antonio", "Parque Berrío", "Universidad", "Caribe", "Acevedo", "Poblado"}
        for estacion in self.estaciones:
            central = estacion in centrales
            perfiles[estacion] = {
                "popularidad": random.uniform(0.7, 1.0) if central else random.uniform(0.2, 0.6),
                "torniquetes_entrada": random.randint(4, 12) if central else random.randint(2, 6),
                "torniquetes_salida": random.randint(4, 10) if central else random.randint(2, 5),
            }
        return perfiles

    def _demanda_horaria(self, hora: float) -> float:
        return (0.08 + math.exp(-((hora - 7.0) ** 2) / 1.5)
                + math.exp(-((hora - 17.5) ** 2) / 1.5)
                + 0.3 * math.exp(-((hora - 12.5) ** 2) / 3))

    def generar_evento(self, estacion: Optional[str] = None, timestamp: Optional[datetime] = None) -> Dict:
        estacion = estacion or random.choice(self.estaciones)
        ts = timestamp or datetime.now()
        perfil = self.perfiles[estacion]
        demanda = self._demanda_horaria(ts.hour + ts.minute / 60.0) * perfil["popularidad"]
        es_finde = ts.weekday() >= 5
        entradas = max(0, int(demanda * (0.55 if es_finde else 1.0) * random.gauss(250, 60)))
        salidas = max(0, int(entradas * random.uniform(0.7, 1.1)))
        return {
            "event_id": f"PAX-{ts.strftime('%Y%m%d%H%M')}-{estacion[:4].upper()}",
            "estacion": estacion, "timestamp": ts.isoformat(), "entradas": entradas,
            "salidas": salidas, "total_personas": entradas + salidas,
            "torniquetes_activos_entrada": perfil["torniquetes_entrada"],
            "torniquetes_activos_salida": perfil["torniquetes_salida"],
            "ocupacion_estimada_pct": round(min(100, entradas / self.CAPACIDAD_TREN * 100), 1),
            "dia_semana": ts.strftime("%A"), "es_fin_de_semana": es_finde,
            "hora_pico": 6 <= ts.hour <= 9 or 16 <= ts.hour <= 19,
        }

    def generar_lote(self, n_minutos: int = 60, inicio: Optional[datetime] = None) -> List[Dict]:
        inicio = inicio or datetime.now().replace(second=0, microsecond=0)
        return [self.generar_evento(estacion=estacion, timestamp=inicio + timedelta(minutes=i))
                for i in range(n_minutos) for estacion in self.estaciones]
