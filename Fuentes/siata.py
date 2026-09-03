"""Compatibilidad con el nombre historico del simulador climatico."""

try:
    from .weather import SimuladorClima
except ImportError:
    from weather import SimuladorClima


SimuladorSIATA = SimuladorClima

__all__ = ["SimuladorClima", "SimuladorSIATA"]
