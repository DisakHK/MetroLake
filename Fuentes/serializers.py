"""Persistencia de datos simulados en formatos de intercambio."""

import csv
import json
import os
from typing import Dict, List


def _prepare_path(path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)


def exportar_json(datos: List[Dict], ruta: str) -> None:
    _prepare_path(ruta)
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, ensure_ascii=False, indent=2, default=str)
    print(f"  [OK] Exportado {len(datos)} registros -> {ruta}")


def exportar_csv(datos: List[Dict], ruta: str) -> None:
    if not datos:
        return
    _prepare_path(ruta)
    with open(ruta, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=datos[0].keys())
        escritor.writeheader()
        escritor.writerows(datos)
    print(f"  [OK] Exportado {len(datos)} registros -> {ruta}")


def exportar_ndjson(datos: List[Dict], ruta: str) -> None:
    _prepare_path(ruta)
    with open(ruta, "w", encoding="utf-8") as archivo:
        for registro in datos:
            archivo.write(json.dumps(registro, ensure_ascii=False, default=str) + "\n")
    print(f"  [OK] Exportado {len(datos)} registros (NDJSON) -> {ruta}")
