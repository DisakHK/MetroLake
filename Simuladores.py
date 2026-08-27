"""
Simuladores de datos sintéticos para el proyecto Metro de Medellín.
Genera datos de: acelerómetros (vibración), torniquetes (pasajeros) y clima (SIATA).
"""

import json
import random
import math
import time
import csv
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# ─── Configuración del Metro de Medellín ───────────────────────────────────────

ESTACIONES = [
    "Niquía", "Bello", "Madera", "Acevedo", "Tricentenario",
    "Caribe", "Universidad", "Hospital", "Prado", "Parque Berrío",
    "San Antonio", "Alpujarra", "Exposiciones", "Industriales",
    "Poblado", "Aguacatala", "Ayurá", "Envigado", "Itagüí",
    "Sabaneta", "La Estrella"
]

TRAMOS = [
    {"id": f"TR-{i+1:03d}", "origen": ESTACIONES[i], "destino": ESTACIONES[i+1],
     "longitud_m": random.randint(800, 2200),
     "antiguedad_anios": random.randint(5, 30),
     "fatiga_base": round(random.uniform(0.15, 0.65), 3)}
    for i in range(len(ESTACIONES) - 1)
]

SENSORES_POR_TRAMO = 3


# ─── 1. Simulador de Acelerómetros (Vibración IoT) ─────────────────────────────

class SimuladorAcelerometro:
    """Genera telemetría de vibración en formato JSON para sensores IoT."""

    def __init__(self, tramos: List[Dict] = None):
        self.tramos = tramos or TRAMOS
        self.sensores = self._crear_sensores()

    def _crear_sensores(self) -> List[Dict]:
        sensores = []
        for tramo in self.tramos:
            for j in range(SENSORES_POR_TRAMO):
                sensores.append({
                    "sensor_id": f"ACC-{tramo['id']}-{j+1}",
                    "tramo_id": tramo["id"],
                    "origen": tramo["origen"],
                    "destino": tramo["destino"],
                    "posicion_m": round(tramo["longitud_m"] * (j + 1) / (SENSORES_POR_TRAMO + 1)),
                    "fatiga_base": tramo["fatiga_base"],
                    "antiguedad": tramo["antiguedad_anios"],
                    "offset_bias": round(random.gauss(0, 0.02), 4)
                })
        return sensores

    def _vibration_rms(self, sensor: Dict, ts: datetime, pasajeros: int = 300,
                       precipitacion_mm: float = 0.0) -> float:
        hora = ts.hour + ts.minute / 60.0
        # Patrón diario: picos en horas punta (6-8h y 17-19h)
        patron = 0.6 + 0.4 * (math.exp(-((hora - 7) ** 2) / 2) +
                               math.exp(-((hora - 17.5) ** 2) / 2))
        base = 1.2 + sensor["fatiga_base"] * 2.5
        carga = 1.0 + (pasajeros / 1500) * 0.8
        lluvia = 1.0 + (precipitacion_mm / 50) * 0.3
        ruido = random.gauss(0, 0.15)
        rms = base * patron * carga * lluvia + ruido + sensor["offset_bias"]
        return round(max(0.1, rms), 4)

    def generar_evento(self, sensor: Dict = None, timestamp: datetime = None,
                       pasajeros: int = None, precipitacion_mm: float = None) -> Dict:
        sensor = sensor or random.choice(self.sensores)
        ts = timestamp or datetime.now()
        pax = pasajeros if pasajeros is not None else random.randint(80, 1200)
        precip = precipitacion_mm if precipitacion_mm is not None else random.uniform(0, 30)
        rms = self._vibration_rms(sensor, ts, pax, precip)
        # Anomalía: fatiga alta + vibración elevada
        es_anomalia = rms > 4.5 and sensor["fatiga_base"] > 0.5
        return {
            "event_id": f"VIB-{ts.strftime('%Y%m%d%H%M%S')}-{sensor['sensor_id']}",
            "sensor_id": sensor["sensor_id"],
            "tramo_id": sensor["tramo_id"],
            "estacion_origen": sensor["origen"],
            "estacion_destino": sensor["destino"],
            "posicion_m": sensor["posicion_m"],
            "timestamp": ts.isoformat(),
            "vibracion_rms_mm_s2": rms,
            "frecuencia_hz": round(random.uniform(5, 120), 2),
        
            "fatiga_acumulada": round(min(1.0, sensor["fatiga_base"] + rms * 0.02), 4),
            "es_anomalia": es_anomalia,
            "pasajeros_estimados": pax,
            "precipitacion_mm": round(precip, 2),
            "unidad": "mm/s²"
        }

    def generar_lote(self, n: int = 100, inicio: datetime = None,
                     intervalo_seg: int = 10) -> List[Dict]:
        inicio = inicio or datetime.now()
        eventos = []
        for i in range(n):
            ts = inicio + timedelta(seconds=i * intervalo_seg)
            sensor = self.sensores[i % len(self.sensores)]
            eventos.append(self.generar_evento(sensor=sensor, timestamp=ts))
        return eventos


# ─── 2. Simulador de Torniquetes (Pasajeros) ───────────────────────────────────

class SimuladorTorniquetes:
    """Genera eventos de conteo de pasajeros por estación y por minuto."""

    CAPACIDAD_TREN = 1500

    def __init__(self, estaciones: List[str] = None):
        self.estaciones = estaciones or ESTACIONES
        self.perfiles = self._crear_perfiles()

    def _crear_perfiles(self) -> Dict[str, Dict]:
        perfiles = {}
        for est in self.estaciones:
            es_central = est in ["San Antonio", "Parque Berrío", "Universidad",
                                  "Caribe", "Acevedo", "Poblado"]
            perfiles[est] = {
                "popularidad": random.uniform(0.7, 1.0) if es_central else random.uniform(0.2, 0.6),
                "torniquetes_entrada": random.randint(4, 12) if es_central else random.randint(2, 6),
                "torniquetes_salida": random.randint(4, 10) if es_central else random.randint(2, 5),
            }
        return perfiles

    def _demanda_horaria(self, hora: float) -> float:
        pico_am = math.exp(-((hora - 7.0) ** 2) / 1.5)
        pico_pm = math.exp(-((hora - 17.5) ** 2) / 1.5)
        mediodia = 0.3 * math.exp(-((hora - 12.5) ** 2) / 3)
        base = 0.08
        return base + pico_am + pico_pm + mediodia

    def generar_evento(self, estacion: str = None, timestamp: datetime = None) -> Dict:
        estacion = estacion or random.choice(self.estaciones)
        ts = timestamp or datetime.now()
        perfil = self.perfiles[estacion]
        hora = ts.hour + ts.minute / 60.0
        demanda = self._demanda_horaria(hora) * perfil["popularidad"]
        # Día de semana vs fin de semana
        es_finde = ts.weekday() >= 5
        factor_dia = 0.55 if es_finde else 1.0
        entradas = max(0, int(demanda * factor_dia * random.gauss(250, 60)))
        salidas = max(0, int(entradas * random.uniform(0.7, 1.1)))
        return {
            "event_id": f"PAX-{ts.strftime('%Y%m%d%H%M')}-{estacion[:4].upper()}",
            "estacion": estacion,
            "timestamp": ts.isoformat(),
            "entradas": entradas,
            "salidas": salidas,
            "total_personas": entradas + salidas,
            "torniquetes_activos_entrada": perfil["torniquetes_entrada"],
            "torniquetes_activos_salida": perfil["torniquetes_salida"],
            "ocupacion_estimada_pct": round(min(100, (entradas / self.CAPACIDAD_TREN) * 100), 1),
            "dia_semana": ts.strftime("%A"),
            "es_fin_de_semana": es_finde,
            "hora_pico": 6 <= ts.hour <= 9 or 16 <= ts.hour <= 19
        }

    def generar_lote(self, n_minutos: int = 60, inicio: datetime = None) -> List[Dict]:
        inicio = inicio or datetime.now().replace(second=0, microsecond=0)
        eventos = []
        for i in range(n_minutos):
            ts = inicio + timedelta(minutes=i)
            for est in self.estaciones:
                eventos.append(self.generar_evento(estacion=est, timestamp=ts))
        return eventos


# ─── 3. Simulador SIATA (Precipitaciones y Clima) ──────────────────────────────

class SimuladorSIATA:
    """Simula datos de precipitación del SIATA para el Valle de Aburrá."""

    PLUVIOMETROS = [
        {"id": "PLV-001", "nombre": "Estación Olaya Herrera", "lat": 6.2204, "lon": -75.5900},
        {"id": "PLV-002", "nombre": "Estación Bello", "lat": 6.3356, "lon": -75.5596},
        {"id": "PLV-003", "nombre": "Estación Itagüí", "lat": 6.1844, "lon": -75.5992},
        {"id": "PLV-004", "nombre": "Estación Envigado", "lat": 6.1714, "lon": -75.5773},
        {"id": "PLV-005", "nombre": "Estación Sabaneta", "lat": 6.1517, "lon": -75.6167},
        {"id": "PLV-006", "nombre": "Estación Caldas", "lat": 6.0893, "lon": -75.6364},
        {"id": "PLV-007", "nombre": "Estación La Estrella", "lat": 6.1583, "lon": -75.6428},
    ]

    NIVELES_ALERTA = [
        {"nivel": "verde", "min_mm": 0, "max_mm": 10},
        {"nivel": "amarilla", "min_mm": 10, "max_mm": 30},
        {"nivel": "naranja", "min_mm": 30, "max_mm": 60},
        {"nivel": "roja", "min_mm": 60, "max_mm": 150},
    ]

    def __init__(self):
        self.estado_lluvia = {}  # Persistencia de estado entre lecturas

    def _patron_estacional(self, ts: datetime) -> float:
        mes = ts.month
        # Medellín: lluvias bimodales (abr-may, sep-nov)
        if mes in [4, 5, 10, 11]:
            return random.uniform(0.6, 1.0)
        elif mes in [3, 6, 9]:
            return random.uniform(0.3, 0.6)
        else:
            return random.uniform(0.05, 0.3)

    def _nivel_alerta(self, precipitacion_mm: float) -> str:
        for nivel in reversed(self.NIVELES_ALERTA):
            if precipitacion_mm >= nivel["min_mm"]:
                return nivel["nivel"]
        return "verde"

    def generar_lectura(self, pluviometro: Dict = None, timestamp: datetime = None) -> Dict:
        pluv = pluviometro or random.choice(self.PLUVIOMETROS)
        ts = timestamp or datetime.now()
        estacional = self._patron_estacional(ts)
        hora = ts.hour
        # Lluvias más frecuentes en la tarde (14-18h)
        factor_hora = 1.0 + 0.8 * math.exp(-((hora - 16) ** 2) / 8)
        esta_lloviendo = random.random() < estacional * 0.6
        if esta_lloviendo:
            intensidad = random.expovariate(1 / (15 * estacional * factor_hora))
            precipitacion = round(min(120, intensidad), 2)
        else:
            precipitacion = round(random.uniform(0, 0.5), 2)

        humedad = round(min(100, 60 + precipitacion * 0.5 + random.gauss(0, 5)), 1)
        temperatura = round(random.gauss(22, 3) - precipitacion * 0.05, 1)

        return {
            "lectura_id": f"SIATA-{ts.strftime('%Y%m%d%H%M')}-{pluv['id']}",
            "pluviometro_id": pluv["id"],
            "nombre_estacion": pluv["nombre"],
            "latitud": pluv["lat"],
            "longitud": pluv["lon"],
            "timestamp": ts.isoformat(),
            "precipitacion_mm_h": precipitacion,
            "precipitacion_acumulada_dia_mm": round(precipitacion * random.uniform(1, 8), 2),
            "humedad_relativa_pct": humedad,
            "temperatura_c": temperatura,
            "nivel_alerta": self._nivel_alerta(precipitacion),
            "esta_lloviendo": esta_lloviendo,
            "velocidad_viento_km_h": round(random.gauss(12, 5), 1),
            "direccion_viento": random.choice(["N", "NE", "E", "SE", "S", "SO", "O", "NO"]),
            "visibilidad_km": round(max(0.5, 10 - precipitacion * 0.1 + random.gauss(0, 1)), 1)
        }

    def generar_lote(self, n_lecturas: int = 50, inicio: datetime = None,
                     intervalo_min: int = 5) -> List[Dict]:
        inicio = inicio or datetime.now()
        lecturas = []
        for i in range(n_lecturas):
            ts = inicio + timedelta(minutes=i * intervalo_min)
            for pluv in self.PLUVIOMETROS:
                lecturas.append(self.generar_lectura(pluviometro=pluv, timestamp=ts))
        return lecturas


# ─── Exportadores de datos ──────────────────────────────────────────────────────

def exportar_json(datos: List[Dict], ruta: str):
    """Exporta una lista de diccionarios a un archivo JSON."""
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2, default=str)
    print(f"  [OK] Exportado {len(datos)} registros -> {ruta}")

def exportar_csv(datos: List[Dict], ruta: str):
    """Exporta una lista de diccionarios a un archivo CSV."""
    if not datos:
        return
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=datos[0].keys())
        writer.writeheader()
        writer.writerows(datos)
    print(f"  [OK] Exportado {len(datos)} registros -> {ruta}")

def exportar_ndjson(datos: List[Dict], ruta: str):
    """Exporta en formato NDJSON (una línea JSON por registro) para streaming."""
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        for registro in datos:
            f.write(json.dumps(registro, ensure_ascii=False, default=str) + "\n")
    print(f"  [OK] Exportado {len(datos)} registros (NDJSON) -> {ruta}")


# ─── Generador integrado ───────────────────────────────────────────────────────

def generar_dataset_completo(
    dias: int = 7,
    intervalo_vibracion_seg: int = 30,
    intervalo_pasajeros_min: int = 1,
    intervalo_clima_min: int = 5,
    directorio_salida: str = "datos_sinteticos"
):
    """
    Genera un dataset completo correlacionado de los 3 simuladores.

    Args:
        dias: Número de días a simular.
        intervalo_vibracion_seg: Segundos entre lecturas de vibración.
        intervalo_pasajeros_min: Minutos entre conteos de pasajeros.
        intervalo_clima_min: Minutos entre lecturas de clima.
        directorio_salida: Carpeta donde se guardarán los archivos.
    """
    print(f"\n{'='*60}")
    print(f"  GENERADOR DE DATOS SINTETICOS - METRO DE MEDELLIN")
    print(f"{'='*60}")
    print(f"  Dias a simular: {dias}")
    print(f"  Directorio: {directorio_salida}/")
    print(f"{'='*60}\n")

    sim_acc = SimuladorAcelerometro()
    sim_pax = SimuladorTorniquetes()
    sim_siata = SimuladorSIATA()

    inicio = datetime.now() - timedelta(days=dias)

    for dia in range(dias):
        fecha_dia = inicio + timedelta(days=dia)
        fecha_str = fecha_dia.strftime("%Y-%m-%d")
        print(f"  Dia {dia+1}/{dias} - {fecha_str}")

        dir_dia = os.path.join(directorio_salida, fecha_str)

        # Clima del día (cada intervalo_clima_min minutos, 24h)
        n_clima = (24 * 60) // intervalo_clima_min
        clima = sim_siata.generar_lote(n_lecturas=n_clima,
                                        inicio=fecha_dia,
                                        intervalo_min=intervalo_clima_min)
        exportar_json(clima, os.path.join(dir_dia, "siata_precipitacion.json"))
        exportar_csv(clima, os.path.join(dir_dia, "siata_precipitacion.csv"))

        # Obtener precipitación promedio del día para correlacionar
        precip_promedio = sum(r["precipitacion_mm_h"] for r in clima) / max(len(clima), 1)

        # Pasajeros del día (cada minuto, solo horario operativo 5-23h)
        horas_operacion = 18  # 5am a 11pm
        n_pasajeros = horas_operacion * 60 // intervalo_pasajeros_min
        inicio_operacion = fecha_dia.replace(hour=5, minute=0, second=0)
        pasajeros = sim_pax.generar_lote(n_minutos=n_pasajeros, inicio=inicio_operacion)
        exportar_csv(pasajeros, os.path.join(dir_dia, "torniquetes_pasajeros.csv"))
        exportar_ndjson(pasajeros, os.path.join(dir_dia, "torniquetes_pasajeros.ndjson"))

        # Vibración (muestreo reducido: cada 5 min por sensor para archivos manejables)
        n_vibracion = (horas_operacion * 60) // 5  # cada 5 minutos
        vibracion = sim_acc.generar_lote(n=n_vibracion * len(sim_acc.sensores) // 10,
                                          inicio=inicio_operacion,
                                          intervalo_seg=intervalo_vibracion_seg)
        exportar_json(vibracion, os.path.join(dir_dia, "acelerometros_vibracion.json"))
        exportar_ndjson(vibracion, os.path.join(dir_dia, "acelerometros_vibracion.ndjson"))

        print()

    # Resumen
    print(f"{'='*60}")
    print(f"  [OK] Generacion completa: {dias} dias de datos")
    print(f"  [OK] Directorio: {directorio_salida}/")
    print(f"{'='*60}\n")


# ─── Modo streaming (simula eventos en tiempo real) ─────────────────────────────

def modo_streaming(intervalo_seg: float = 1.0, duracion_seg: int = 60):
    """
    Simula emisión de eventos en tiempo real por consola (stdout).
    Útil para pruebas con Pub/Sub o Kafka.
    """
    print(f"\n  >> Modo streaming iniciado (intervalo={intervalo_seg}s, duracion={duracion_seg}s)")
    print(f"  Presiona Ctrl+C para detener.\n")

    sim_acc = SimuladorAcelerometro()
    sim_pax = SimuladorTorniquetes()
    sim_siata = SimuladorSIATA()

    inicio = time.time()
    contador = 0

    try:
        while time.time() - inicio < duracion_seg:
            ts = datetime.now()
            tipo = random.choices(
                ["vibracion", "pasajeros", "clima"],
                weights=[0.5, 0.35, 0.15]
            )[0]

            if tipo == "vibracion":
                evento = sim_acc.generar_evento(timestamp=ts)
            elif tipo == "pasajeros":
                evento = sim_pax.generar_evento(timestamp=ts)
            else:
                evento = sim_siata.generar_lectura(timestamp=ts)

            evento["_tipo_fuente"] = tipo
            print(json.dumps(evento, ensure_ascii=False, default=str))
            contador += 1
            time.sleep(intervalo_seg)
    except KeyboardInterrupt:
        pass

    print(f"\n  [STOP] Streaming detenido. Total eventos emitidos: {contador}")


# ─── Punto de entrada ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "streaming":
        duracion = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        modo_streaming(intervalo_seg=0.5, duracion_seg=duracion)
    else:
        dias = int(sys.argv[1]) if len(sys.argv) > 1 else 3
        generar_dataset_completo(dias=dias, directorio_salida="datos_sinteticos")
