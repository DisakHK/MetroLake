import requests
from datetime import datetime
from typing import List, Dict

class IngestaOpenMeteo:
    """Ingesta de datos reales de Open-Meteo para el Valle de Aburrá."""

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

    def _nivel_alerta(self, precipitacion_mm: float) -> str:
        for nivel in reversed(self.NIVELES_ALERTA):
            if precipitacion_mm >= nivel["min_mm"]:
                return nivel["nivel"]
        return "verde"

    def _grados_a_cardinal(self, grados: float) -> str:
        """Convierte la dirección del viento de grados (0-360) a puntos cardinales."""
        direcciones = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]
        # Se divide entre 45 (ya que 360/8 = 45 grados por dirección)
        # Se suma 0.5 para redondear al sector más cercano
        indice = int((grados / 45) + 0.5) % 8
        return direcciones[indice]

    def obtener_lecturas_actuales(self) -> List[Dict]:
        """Hace una única petición HTTP para obtener el clima de todas las estaciones."""
        
        # 1. Extraemos las coordenadas usando 'List Comprehension'
        lats = [str(p["lat"]) for p in self.PLUVIOMETROS]
        lons = [str(p["lon"]) for p in self.PLUVIOMETROS]

        url = "https://api.open-meteo.com/v1/forecast"
        
        # 2. Parámetros de la petición. Open-Meteo permite pasar listas separadas por comas.
        params = {
            "latitude": ",".join(lats),
            "longitude": ",".join(lons),
            "current": ["temperature_2m", "relative_humidity_2m", "precipitation", "wind_speed_10m", "wind_direction_10m"],
            "daily": ["precipitation_sum"], # Para calcular la lluvia acumulada del día
            "timezone": "America/Bogota"
        }

        # 3. Petición GET a la API
        try:
            response = requests.get(url, params=params)
            response.raise_for_status() # Lanza una excepción si el código HTTP es un error (ej. 404, 500)
            datos_api = response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error al conectar con la API: {e}")
            return []

        lecturas = []
        ts = datetime.now()

        # 4. Zip une dos o más listas iterándolas al mismo tiempo
        for pluv, datos_estacion in zip(self.PLUVIOMETROS, datos_api):
            current = datos_estacion.get("current", {})
            daily = datos_estacion.get("daily", {})

            # Extracción segura de los datos con fallback a 0.0 si el dato no existe
            precipitacion = current.get("precipitation", 0.0)
            precipitacion_acumulada = daily.get("precipitation_sum", [0.0])[0]
            
            lectura = {
                "lectura_id": f"OM-{ts.strftime('%Y%m%d%H%M')}-{pluv['id']}",
                "pluviometro_id": pluv["id"],
                "nombre_estacion": pluv["nombre"],
                "latitud": pluv["lat"],
                "longitud": pluv["lon"],
                "timestamp": ts.isoformat(),
                "precipitacion_mm_h": precipitacion,
                "precipitacion_acumulada_dia_mm": precipitacion_acumulada,
                "humedad_relativa_pct": current.get("relative_humidity_2m", 0),
                "temperatura_c": current.get("temperature_2m", 0.0),
                "nivel_alerta": self._nivel_alerta(precipitacion),
                "esta_lloviendo": precipitacion > 0.0,
                "velocidad_viento_km_h": current.get("wind_speed_10m", 0.0),
                "direccion_viento": self._grados_a_cardinal(current.get("wind_direction_10m", 0)),
                "visibilidad_km": 10.0 # Open-Meteo requiere otra capa para visibilidad, dejamos 10.0 como base.
            }
            lecturas.append(lectura)

        return lecturas

# Ejemplo de uso:
if __name__ == "__main__":
    ingesta = IngestaOpenMeteo()
    datos_reales = ingesta.obtener_lecturas_actuales()
    for dato in datos_reales:
        print(f"{dato['nombre_estacion']}: Lluvia={dato['precipitacion_mm_h']}mm | Alerta={dato['nivel_alerta']}")