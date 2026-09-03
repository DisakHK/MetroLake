"""Punto de entrada para ejecutar todos los simuladores del proyecto."""

import sys

try:
    from .accelerometer import SimuladorAcelerometro
    from .dataset import generar_dataset_completo
    from .serializers import exportar_csv, exportar_json, exportar_ndjson
    from .streaming import modo_streaming
    from .weather import SimuladorClima
    from .turnstiles import SimuladorTorniquetes
except ImportError:
    from accelerometer import SimuladorAcelerometro
    from dataset import generar_dataset_completo
    from serializers import exportar_csv, exportar_json, exportar_ndjson
    from streaming import modo_streaming
    from weather import SimuladorClima
    from turnstiles import SimuladorTorniquetes


def ejecutar_simuladores(dias=3, directorio_salida="datos_sinteticos"):
    """Ejecuta torniquetes, vibracion y clima en una sola generacion."""
    return generar_dataset_completo(dias=dias, directorio_salida=directorio_salida)


__all__ = [
    "SimuladorAcelerometro", "SimuladorTorniquetes", "SimuladorClima",
    "ejecutar_simuladores", "generar_dataset_completo", "modo_streaming",
    "exportar_json", "exportar_csv", "exportar_ndjson",
]


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "streaming":
        duracion = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        salida = sys.argv[3] if len(sys.argv) > 3 else "datos_streaming"
        modo_streaming(intervalo_seg=0.5, duracion_seg=duracion, directorio_salida=salida)
    else:
        dias = int(sys.argv[1]) if len(sys.argv) > 1 else 3
        ejecutar_simuladores(dias=dias)