"""Lanzador de compatibilidad para los simuladores del proyecto."""

import sys

from Ejecucion.simuladores import (
    SimuladorAcelerometro,
    SimuladorClima,
    SimuladorTorniquetes,
    generar_dataset_completo,
    modo_streaming,
)

__all__ = [
    "SimuladorAcelerometro", "SimuladorTorniquetes", "SimuladorClima",
    "generar_dataset_completo", "modo_streaming",
]


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "streaming":
        duracion = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        modo_streaming(intervalo_seg=0.5, duracion_seg=duracion)
    else:
        dias = int(sys.argv[1]) if len(sys.argv) > 1 else 3
        generar_dataset_completo(dias=dias)
