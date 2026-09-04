"""Publicador de eventos de los simuladores hacia Google Cloud Pub/Sub."""

import json
import os
import random
import time
from datetime import datetime
from typing import Dict, Mapping, Optional

try:
    from ..Fuentes.accelerometer import SimuladorAcelerometro
    from ..Fuentes.turnstiles import SimuladorTorniquetes
    from ..Fuentes.weather import SimuladorClima
except ImportError:
    from Fuentes.accelerometer import SimuladorAcelerometro
    from Fuentes.turnstiles import SimuladorTorniquetes
    from Fuentes.weather import SimuladorClima


TIPOS_EVENTO = ("vibracion", "pasajeros", "clima")


def _obtener_configuracion() -> Dict[str, str]:
    """Lee el proyecto y los temas desde variables de entorno."""
    nombres = {
        "project_id": "GCP_PROJECT_ID",
        "vibracion": "GCP_TOPIC_VIBRACION",
        "pasajeros": "GCP_TOPIC_PASAJEROS",
        "clima": "GCP_TOPIC_CLIMA",
    }
    configuracion = {clave: os.getenv(variable, "") for clave, variable in nombres.items()}
    faltantes = [variable for clave, variable in nombres.items() if not configuracion[clave]]
    if faltantes:
        raise RuntimeError(
            "Faltan variables de entorno para Pub/Sub: " + ", ".join(faltantes)
        )
    return configuracion


def _crear_rutas_pubsub(publisher, configuracion: Mapping[str, str]) -> Dict[str, str]:
    return {
        tipo: publisher.topic_path(configuracion["project_id"], configuracion[tipo])
        for tipo in TIPOS_EVENTO
    }


def _generar_evento(tipo: str, simuladores: Mapping[str, object], timestamp: datetime) -> Dict:
    if tipo == "vibracion":
        return simuladores[tipo].generar_evento(timestamp=timestamp)
    if tipo == "pasajeros":
        return simuladores[tipo].generar_evento(timestamp=timestamp)
    return simuladores[tipo].generar_lectura(timestamp=timestamp)


def modo_streaming_directo_gcp(
    intervalo_seg: float = 1.0,
    duracion_seg: int = 60,
    publisher=None,
    configuracion: Optional[Mapping[str, str]] = None,
) -> None:
    """Genera eventos y los publica en tres temas independientes de Pub/Sub.

    ``publisher`` y ``configuracion`` son opcionales para facilitar pruebas.
    En ejecucion normal se crea PublisherClient y se leen variables de entorno.
    """
    if publisher is None:
        try:
            from google.cloud import pubsub_v1
        except ImportError as error:
            raise RuntimeError(
                "Instala la dependencia con: pip install google-cloud-pubsub"
            ) from error
        publisher = pubsub_v1.PublisherClient()
    configuracion = configuracion or _obtener_configuracion()
    rutas = _crear_rutas_pubsub(publisher, configuracion)
    simuladores = {
        "vibracion": SimuladorAcelerometro(),
        "pasajeros": SimuladorTorniquetes(),
        "clima": SimuladorClima(),
    }

    inicio = time.time()
    try:
        while time.time() - inicio < duracion_seg:
            timestamp = datetime.now()
            tipo = random.choices(list(TIPOS_EVENTO), weights=[0.5, 0.35, 0.15])[0]
            evento = _generar_evento(tipo, simuladores, timestamp)
            mensaje = json.dumps(evento, ensure_ascii=False, default=str).encode("utf-8")
            future = publisher.publish(rutas[tipo], mensaje)
            print(f"Enviado {tipo} -> ID GCP: {future.result()}")
            time.sleep(intervalo_seg)
    except KeyboardInterrupt:
        print("\nStreaming GCP detenido por el usuario.")


if __name__ == "__main__":
    duracion = int(os.getenv("GCP_DURACION_SEG", "60"))
    intervalo = float(os.getenv("GCP_INTERVALO_SEG", "1"))
    modo_streaming_directo_gcp(intervalo_seg=intervalo, duracion_seg=duracion)
