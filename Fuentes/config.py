"""Configuracion compartida del Metro de Medellin."""

ESTACIONES = [
    "Niquía", "Bello", "Madera", "Acevedo", "Tricentenario",
    "Caribe", "Universidad", "Hospital", "Prado", "Parque Berrío",
    "San Antonio", "Alpujarra", "Exposiciones", "Industriales",
    "Poblado", "Aguacatala", "Ayurá", "Envigado", "Itagüí",
    "Sabaneta", "La Estrella"
]

SENSORES_POR_TRAMO = 3


def crear_tramos():
    import random

    return [
        {
            "id": f"TR-{i + 1:03d}",
            "origen": ESTACIONES[i],
            "destino": ESTACIONES[i + 1],
            "longitud_m": random.randint(800, 2200),
            "antiguedad_anios": random.randint(5, 30),
            "fatiga_base": round(random.uniform(0.15, 0.65), 3),
        }
        for i in range(len(ESTACIONES) - 1)
    ]


TRAMOS = crear_tramos()
