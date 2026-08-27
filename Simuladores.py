"""
Simuladores de datos sintéticos para el proyecto Metro de Medellín.
Genera datos de: acelerómetros (vibración), torniquetes (pasajeros) y clima (SIATA).
Incluye ingesta de API Open-Meteo con fallback a simulación.
"""

import json
import random
import requests
import math
import time
import csv
import os
from datetime import datetime, timedelta
from typing import List, Dict

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

    def _vibration_rms(self, sensor: Dict, ts: datetime, pasajeros: int = 300, precipitacion_mm: float = 0.0) -> float:
        hora = ts.hour + ts.minute / 60.0
        patron = 0.6 + 0.4 * (math.exp(-((hora - 7) ** 2) / 2) + math.exp(-((hora - 17.5) ** 2) / 2))
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

    def generar_lote(self, n: int = 100, inicio: datetime = None, intervalo_seg: int = 10) -> List[Dict]:
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
            es_central = est in ["San Antonio", "Parque Berrío", "Universidad", "Caribe", "Acevedo", "Poblado"]
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
        return 0.08 + pico_am + pico_pm + mediodia

    def generar_evento(self, estacion: str = None, timestamp: datetime = None) -> Dict:
        estacion = estacion or random.choice(self.estaciones)
        ts = timestamp or datetime.now()
        perfil = self.perfiles[estacion]
        hora = ts.hour + ts.minute / 60.0
        demanda = self._demanda_horaria(hora) * perfil["popularidad"]
        
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
    """Ingesta datos de Open-Meteo con fallback a simulación sintética."""

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
        self.cache_api = {}
        self.ultima_llamada_api = None

    def _patron_estacional(self, ts: datetime) -> float:
        mes = ts.month
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

    def _grados_a_cardinal(self, grados: float) -> str:
        direcciones = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]
        indice = int((grados / 45) + 0.5) % 8
        return direcciones[indice]

    def _intentar_api(self) -> bool:
        """Intenta actualizar los datos del clima desde la API."""
        ahora = datetime.now()
        
        # Evita llamar a la API múltiples veces por segundo si está en un bucle
        if self.ultima_llamada_api and (ahora - self.ultima_llamada_api).total_seconds() < 300:
            return bool(self.cache_api)

        lats = [str(p["lat"]) for p in self.PLUVIOMETROS]
        lons = [str(p["lon"]) for p in self.PLUVIOMETROS]
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": ",".join(lats),
            "longitude": ",".join(lons),
            "current": ["temperature_2m", "relative_humidity_2m", "precipitation", "wind_speed_10m", "wind_direction_10m"],
            "daily": ["precipitation_sum"],
            "timezone": "America/Bogota"
        }

        try:
            # timeout=5 evita que el programa se quede congelado si la API no responde
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            datos_api = response.json()
            
            # Si responde correctamente, mapeamos los datos al caché
            if isinstance(datos_api, list):
                for pluv, datos_estacion in zip(self.PLUVIOMETROS, datos_api):
                    current = datos_estacion.get("current", {})
                    daily = datos_estacion.get("daily", {})
                    self.cache_api[pluv["id"]] = {
                        "precipitacion": current.get("precipitation", 0.0),
                        "precip_acumulada": daily.get("precipitation_sum", [0.0])[0],
                        "humedad": current.get("relative_humidity_2m", 0),
                        "temperatura": current.get("temperature_2m", 0.0),
                        "vel_viento": current.get("wind_speed_10m", 0.0),
                        "dir_viento": self._grados_a_cardinal(current.get("wind_direction_10m", 0))
                    }
                self.ultima_llamada_api = ahora
                return True
        except requests.exceptions.RequestException:
            # Captura silenciosamente cualquier error (sin internet, API caída, etc.)
            return False
            
        return False

    def generar_lectura(self, pluviometro: Dict = None, timestamp: datetime = None) -> Dict:
        pluv = pluviometro or random.choice(self.PLUVIOMETROS)
        ts = timestamp or datetime.now()
        
        # Validación de contexto temporal:
        # Solo usamos la API si el dato solicitado es reciente (menos de 2 horas de diferencia)
        es_tiempo_real = abs((datetime.now() - ts).total_seconds()) < 7200
        
        # 1. INTENTO DE USO DE API
        if es_tiempo_real and self._intentar_api() and pluv["id"] in self.cache_api:
            datos = self.cache_api[pluv["id"]]
            precipitacion = datos["precipitacion"]
            precip_acumulada = datos["precip_acumulada"]
            humedad = datos["humedad"]
            temperatura = datos["temperatura"]
            vel_viento = datos["vel_viento"]
            dir_viento = datos["dir_viento"]
            esta_lloviendo = precipitacion > 0.0
            
        # 2. FALLBACK (CATCH SINTÉTICO)
        else:
            estacional = self._patron_estacional(ts)
            hora = ts.hour
            factor_hora = 1.0 + 0.8 * math.exp(-((hora - 16) ** 2) / 8)
            esta_lloviendo = random.random() < estacional * 0.6
            
            if esta_lloviendo:
                intensidad = random.expovariate(1 / (15 * estacional * factor_hora))
                precipitacion = round(min(120, intensidad), 2)
            else:
                precipitacion = round(random.uniform(0, 0.5), 2)

            humedad = round(min(100, 60 + precipitacion * 0.5 + random.gauss(0, 5)), 1)
            temperatura = round(random.gauss(22, 3) - precipitacion * 0.05, 1)
            precip_acumulada = round(precipitacion * random.uniform(1, 8), 2)
            vel_viento = round(random.gauss(12, 5), 1)
            dir_viento = random.choice(["N", "NE", "E", "SE", "S", "SO", "O", "NO"])

        return {
            "lectura_id": f"SIATA-{ts.strftime('%Y%m%d%H%M')}-{pluv['id']}",
            "pluviometro_id": pluv["id"],
            "nombre_estacion": pluv["nombre"],
            "latitud": pluv["lat"],
            "longitud": pluv["lon"],
            "timestamp": ts.isoformat(),
            "precipitacion_mm_h": precipitacion,
            "precipitacion_acumulada_dia_mm": precip_acumulada,
            "humedad_relativa_pct": humedad,
            "temperatura_c": temperatura,
            "nivel_alerta": self._nivel_alerta(precipitacion),
            "esta_lloviendo": esta_lloviendo,
            "velocidad_viento_km_h": vel_viento,
            "direccion_viento": dir_viento,
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
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2, default=str)
    print(f"  [OK] Exportado {len(datos)} registros -> {ruta}")

def exportar_csv(datos: List[Dict], ruta: str):
    if not datos:
        return
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=datos[0].keys())
        writer.writeheader()
        writer.writerows(datos)
    print(f"  [OK] Exportado {len(datos)} registros -> {ruta}")

def exportar_ndjson(datos: List[Dict], ruta: str):
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

        n_clima = (24 * 60) // intervalo_clima_min
        clima = sim_siata.generar_lote(n_lecturas=n_clima,
                                       inicio=fecha_dia,
                                       intervalo_min=intervalo_clima_min)
        exportar_json(clima, os.path.join(dir_dia, "siata_precipitacion.json"))
        exportar_csv(clima, os.path.join(dir_dia, "siata_precipitacion.csv"))

        horas_operacion = 18 
        n_pasajeros = horas_operacion * 60 // intervalo_pasajeros_min
        inicio_operacion = fecha_dia.replace(hour=5, minute=0, second=0)
        pasajeros = sim_pax.generar_lote(n_minutos=n_pasajeros, inicio=inicio_operacion)
        exportar_csv(pasajeros, os.path.join(dir_dia, "torniquetes_pasajeros.csv"))
        exportar_ndjson(pasajeros, os.path.join(dir_dia, "torniquetes_pasajeros.ndjson"))

        n_vibracion = (horas_operacion * 60) // 5 
        vibracion = sim_acc.generar_lote(n=n_vibracion * len(sim_acc.sensores) // 10,
                                         inicio=inicio_operacion,
                                         intervalo_seg=intervalo_vibracion_seg)
        exportar_json(vibracion, os.path.join(dir_dia, "acelerometros_vibracion.json"))
        exportar_ndjson(vibracion, os.path.join(dir_dia, "acelerometros_vibracion.ndjson"))

        print()

    print(f"{'='*60}")
    print(f"  [OK] Generacion completa: {dias} dias de datos")
    print(f"  [OK] Directorio: {directorio_salida}/")
    print(f"{'='*60}\n")


# ─── Modo streaming (simula eventos en tiempo real) ─────────────────────────────

def modo_streaming(intervalo_seg: float = 1.0, duracion_seg: int = 60):
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