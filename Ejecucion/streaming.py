"""Ejecucion del modo streaming de eventos."""

import json
import random
import time
from datetime import datetime

try:
    from ..Fuentes.accelerometer import SimuladorAcelerometro
    from ..Persistencia.serializers import exportar_json
    from ..Fuentes.weather import SimuladorClima
    from ..Fuentes.turnstiles import SimuladorTorniquetes
except ImportError:
    from Fuentes.accelerometer import SimuladorAcelerometro
    from Persistencia.serializers import exportar_json
    from Fuentes.weather import SimuladorClima
    from Fuentes.turnstiles import SimuladorTorniquetes


def modo_streaming(intervalo_seg=1.0, duracion_seg=60, directorio_salida="datos_streaming"):
    simuladores = {
        "vibracion": SimuladorAcelerometro(),
        "pasajeros": SimuladorTorniquetes(),
        "clima": SimuladorClima(),
    }
    eventos = []
    inicio = time.time()
    try:
        while time.time() - inicio < duracion_seg:
            timestamp = datetime.now()
            tipo = random.choices(list(simuladores), weights=[0.5, 0.35, 0.15])[0]
            simulador = simuladores[tipo]
            if tipo == "vibracion":
                evento = simulador.generar_evento(timestamp=timestamp)
            elif tipo == "pasajeros":
                evento = simulador.generar_evento(timestamp=timestamp)
            else:
                evento = simulador.generar_lectura(timestamp=timestamp)
            evento["_tipo_fuente"] = tipo
            eventos.append(evento)
            print(json.dumps(evento, ensure_ascii=False, default=str))
            time.sleep(intervalo_seg)
    except KeyboardInterrupt:
        pass
    ruta = f"{directorio_salida}/streaming_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    exportar_json(eventos, ruta)
    print(f"\n[STOP] Streaming detenido. Total eventos emitidos: {len(eventos)}")
