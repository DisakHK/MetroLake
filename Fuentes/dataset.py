"""Orquestacion de la generacion de datasets historicos."""

import os
from datetime import datetime, timedelta

try:
    from .accelerometer import SimuladorAcelerometro
    from .config import TRAMOS
    from .serializers import exportar_csv, exportar_json, exportar_ndjson
    from .weather import SimuladorClima
    from .turnstiles import SimuladorTorniquetes
except ImportError:
    from accelerometer import SimuladorAcelerometro
    from config import TRAMOS
    from serializers import exportar_csv, exportar_json, exportar_ndjson
    from weather import SimuladorClima
    from turnstiles import SimuladorTorniquetes


def generar_dataset_completo(dias=7, intervalo_vibracion_seg=30, intervalo_pasajeros_min=1,
                              intervalo_clima_min=5, directorio_salida="datos_sinteticos"):
    simulador_acc = SimuladorAcelerometro(TRAMOS)
    simulador_pax = SimuladorTorniquetes()
    simulador_clima = SimuladorClima()
    inicio = datetime.now() - timedelta(days=dias)
    for dia in range(dias):
        fecha = inicio + timedelta(days=dia)
        carpeta = os.path.join(directorio_salida, fecha.strftime("%Y-%m-%d"))
        clima = simulador_clima.generar_lote((24 * 60) // intervalo_clima_min, fecha, intervalo_clima_min)
        exportar_json(clima, os.path.join(carpeta, "clima_precipitacion.json"))
        exportar_csv(clima, os.path.join(carpeta, "clima_precipitacion.csv"))
        inicio_operacion = fecha.replace(hour=5, minute=0, second=0)
        pasajeros = simulador_pax.generar_lote(18 * 60 // intervalo_pasajeros_min, inicio_operacion)
        exportar_csv(pasajeros, os.path.join(carpeta, "torniquetes_pasajeros.csv"))
        exportar_ndjson(pasajeros, os.path.join(carpeta, "torniquetes_pasajeros.ndjson"))
        vibracion = simulador_acc.generar_lote((18 * 60 // 5) * len(simulador_acc.sensores) // 10, inicio_operacion, intervalo_vibracion_seg)
        exportar_json(vibracion, os.path.join(carpeta, "acelerometros_vibracion.json"))
        exportar_ndjson(vibracion, os.path.join(carpeta, "acelerometros_vibracion.ndjson"))
