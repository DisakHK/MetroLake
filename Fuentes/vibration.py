"""Compatibilidad con el nombre historico del simulador de vibracion."""

try:
	from .accelerometer import SimuladorAcelerometro
except ImportError:
	from accelerometer import SimuladorAcelerometro

__all__ = ["SimuladorAcelerometro"]
