# Proyecto Metro

Proyecto de simulacion y generacion de datos para el Metro de Medellin. El sistema produce tres tipos de informacion:

- **Torniquetes y pasajeros:** entradas, salidas, ocupacion estimada y horas pico por estacion.
- **Vibracion:** telemetria de acelerometros instalada en los tramos de la via.
- **Clima:** precipitacion, acumulado diario, estado de lluvia y nivel de alerta por pluviometro.

El clima intenta obtener datos actuales desde la API publica de [Open-Meteo](https://open-meteo.com/). Si no hay conexion, la respuesta falla o la fecha solicitada no es actual, se generan datos climaticos sinteticos mediante el fallback incluido en `SimuladorClima`.

## 1. Requisitos

- Windows, macOS o Linux.
- Python 3.9 o una version posterior.
- Conexion a internet solamente para intentar consultar Open-Meteo. El proyecto puede funcionar sin internet gracias al fallback climatico.
- Dependencia de Python: `requests`.

No se requiere una base de datos ni un servidor local. Los resultados se escriben como archivos en el disco.

## 2. Instalacion en Windows

Abre PowerShell en la carpeta raiz del proyecto:

```powershell
cd "C:\ruta\al\ProyectoMetro"
```

Se recomienda crear un entorno virtual:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea la activacion del entorno, puede ejecutarse una sola vez para el usuario actual:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Instala la dependencia:

```powershell
python -m pip install --upgrade pip
python -m pip install requests
python -m pip install google-cloud-pubsub
```

Verifica que Python este disponible:

```powershell
python --version
```

## 3. Estructura del proyecto

```text
ProyectoMetro/
|-- README.md
|-- Fuentes/              # Generadores y fuentes de datos
|   |-- accelerometer.py   # Simulador de telemetria de vibracion
|   |-- config.py          # Estaciones, tramos y cantidad de sensores
|   |-- siata.py           # Alias de compatibilidad del nombre antiguo
|   |-- turnstiles.py      # Simulador de torniquetes y pasajeros
|   |-- vibration.py       # Alias historico del acelerometro
|   |-- weather.py         # Logica exclusiva del clima
|-- Ejecucion/            # Batch, streaming y coordinacion
|   |-- dataset.py
|   |-- simuladores.py
|   `-- streaming.py
|-- Persistencia/         # Exportacion a JSON, CSV y NDJSON
|   `-- serializers.py
|-- Integraciones/        # Conexion con servicios externos
|   `-- publicador_gcp.py
|-- datos_sinteticos/      # Salidas historicas, si se generan
|-- datos_streaming/       # Salidas del modo streaming, si se generan
|-- consulta_clima_api.py  # Consulta directa de datos actuales de Open-Meteo
|-- ejecutar_simuladores.py# Lanzador de compatibilidad para todos los simuladores
```

La ejecucion principal esta en `Ejecucion/simuladores.py`. `Fuentes/weather.py` no ejecuta todos los simuladores ni genera archivos al importarse: contiene unicamente la clase `SimuladorClima` y su logica de API/fallback.

## 4. Ejecucion rapida

Desde la raiz del proyecto, genera tres dias de datos historicos:

```powershell
python -m Ejecucion.simuladores
```

Tambien se puede indicar la cantidad de dias:

```powershell
python -m Ejecucion.simuladores 1
```

El comando crea o completa `datos_sinteticos/` con una carpeta por cada dia generado.

Para ejecutar el modo streaming durante 60 segundos:

```powershell
python -m Ejecucion.simuladores streaming
```

La sintaxis completa del streaming es:

```powershell
python -m Ejecucion.simuladores streaming <duracion_segundos> <directorio_salida>
```

Ejemplo:

```powershell
python -m Ejecucion.simuladores streaming 120 datos_streaming
```

Durante el streaming cada evento se imprime en la consola y, al terminar, se guarda un archivo JSON en el directorio indicado. Se puede detener antes con `Ctrl+C`; los eventos acumulados se exportan igualmente.

## 5. Generacion historica

La funcion principal es `generar_dataset_completo` en `Ejecucion/dataset.py`:

```python
generar_dataset_completo(
    dias=7,
    intervalo_vibracion_seg=30,
    intervalo_pasajeros_min=1,
    intervalo_clima_min=5,
    directorio_salida="datos_sinteticos",
)
```

Parametros:

| Parametro | Valor por defecto | Descripcion |
|---|---:|---|
| `dias` | `7` | Cantidad de carpetas diarias que se generan. |
| `intervalo_vibracion_seg` | `30` | Separacion temporal usada en eventos de vibracion. |
| `intervalo_pasajeros_min` | `1` | Separacion temporal de los eventos de pasajeros. |
| `intervalo_clima_min` | `5` | Separacion temporal de las lecturas climaticas. |
| `directorio_salida` | `datos_sinteticos` | Carpeta raiz para las salidas. |

Cada dia se procesa de la siguiente forma:

1. Se generan lecturas climaticas para 24 horas y todos los pluviometros.
2. Se generan eventos de pasajeros para 18 horas de operacion, desde las 05:00.
3. Se generan eventos de vibracion para los sensores configurados.
4. Cada conjunto se exporta en los formatos definidos por el proyecto.

El numero de registros depende de los intervalos. Por ejemplo, con un dia, `intervalo_clima_min=60` e `intervalo_pasajeros_min=60`, se producen 168 lecturas climaticas y 378 eventos de pasajeros. Los datos de vibracion dependen del numero de tramos y sensores.

## 6. Modo streaming

`modo_streaming` esta en `Ejecucion/streaming.py` y recibe:

```python
modo_streaming(
    intervalo_seg=1.0,
    duracion_seg=60,
    directorio_salida="datos_streaming",
)
```

En cada ciclo selecciona aleatoriamente una fuente con estos pesos aproximados:

- Vibracion: 50%.
- Pasajeros: 35%.
- Clima: 15%.

Cada evento recibe el campo adicional `_tipo_fuente`, cuyo valor es `vibracion`, `pasajeros` o `clima`.

## 7. Publicacion directa en Google Cloud Pub/Sub

El modulo `Integraciones/publicador_gcp.py` reutiliza los tres simuladores existentes y publica cada tipo de evento en un tema independiente:

```text
vibracion  -> tema-metro-vibracion
pasajeros  -> tema-metro-pasajeros
clima      -> tema-metro-clima
```

Con la configuracion que ya quedó validada en este proyecto, usa estos valores reales:

```powershell
[System.Environment]::SetEnvironmentVariable("GCP_PROJECT_ID", "terraform-demo-metro", "Process")
[System.Environment]::SetEnvironmentVariable("GCP_TOPIC_VIBRACION", "tema-metro-vibracion", "Process")
[System.Environment]::SetEnvironmentVariable("GCP_TOPIC_PASAJEROS", "tema-metro-pasajeros", "Process")
[System.Environment]::SetEnvironmentVariable("GCP_TOPIC_CLIMA", "tema-metro-clima", "Process")
[System.Environment]::SetEnvironmentVariable("GCP_DURACION_SEG", "60", "Process")
[System.Environment]::SetEnvironmentVariable("GCP_INTERVALO_SEG", "1", "Process")
```

Si ya tienes permisos suficientes en la cuenta de Google y quieres ejecutar el proyecto desde tu equipo local, primero autentica la sesion de tu usuario con ADC:

```powershell
gcloud auth login
gcloud auth application-default login
gcloud config set project terraform-demo-metro
```

Como ya se comprobó en este proyecto, no es necesario usar `GOOGLE_APPLICATION_CREDENTIALS` si vas a trabajar con tu cuenta de usuario autenticada localmente. Solo se usa cuando se quiere forzar una cuenta de servicio JSON.

Ejecuta el publicador desde la raíz del proyecto:

```powershell
python -m Integraciones.publicador_gcp
```

Por defecto publica durante 60 segundos. Puedes cambiar la duración y el intervalo con `GCP_DURACION_SEG` y `GCP_INTERVALO_SEG`. Este módulo no modifica los simuladores ni reemplaza el streaming local.

### Verificar que los topics existen

```powershell
gcloud pubsub topics list --project=terraform-demo-metro
```

La salida esperada incluye:

```text
projects/terraform-demo-metro/topics/tema-metro-vibracion
projects/terraform-demo-metro/topics/tema-metro-pasajeros
projects/terraform-demo-metro/topics/tema-metro-clima
```

### Diferencia entre topic y subscription

- `tema-metro-clima`, `tema-metro-pasajeros`, `tema-metro-vibracion` son los topics que recibe el publicador.
- `sub-metro-clima-bq`, `sub-metro-pass-bq`, `sub-metro-vib-bq` son las subscriptions que conectan esos mensajes con BigQuery.

El script `Integraciones/publicador_gcp.py` solo necesita los topics, no las subscriptions.

## 8. Funcionamiento del clima y fallback

La clase `SimuladorClima` esta en `Fuentes/weather.py`.

### Consulta a Open-Meteo

La clase consulta:

```text
https://api.open-meteo.com/v1/forecast
```

Solicita únicamente los datos necesarios para el análisis de precipitaciones:

- Precipitacion actual (`precipitation`).
- Precipitacion acumulada del dia (`precipitation_sum`).

El `nivel_alerta` y `esta_lloviendo` no son campos que entregue Open-Meteo: se calculan en el proyecto a partir de la precipitacion. La consulta usa las coordenadas de siete pluviometros del Valle de Aburra y la zona horaria `America/Bogota`.

La respuesta se almacena en memoria durante cinco minutos para evitar consultas repetidas.

### Cuando se usa el fallback

El simulador no sustituye los datos validos de Open-Meteo. Genera datos sinteticos unicamente cuando ocurre cualquiera de estas situaciones:

- No hay conexion a internet.
- La API devuelve un error HTTP o una respuesta no valida.
- La lectura corresponde a una fecha con mas de dos horas de diferencia respecto a la hora actual.

Si la API responde, sus valores de precipitacion se conservan. Si la API no esta disponible o falta un valor, el fallback genera únicamente los valores de precipitacion necesarios para conservar el mismo esquema y permitir que el batch o el streaming continuen funcionando.

Ejemplo de uso directo:

```python
from datetime import datetime
from Fuentes.weather import SimuladorClima

clima = SimuladorClima()
lectura = clima.generar_lectura(timestamp=datetime.now())
print(lectura)

lote = clima.generar_lote(n_lecturas=10, intervalo_min=5)
print(len(lote))
```

## 8. Simuladores

### Torniquetes: `SimuladorTorniquetes`

Esta clase usa las estaciones de `config.py`. Para cada estacion crea un perfil con popularidad y cantidad de torniquetes de entrada y salida. La demanda varia por hora, con picos aproximados en la manana y la tarde, y se reduce durante el fin de semana.

Metodos principales:

```python
from Fuentes.turnstiles import SimuladorTorniquetes

simulador = SimuladorTorniquetes()
evento = simulador.generar_evento()
lote = simulador.generar_lote(n_minutos=60)
```

Un evento incluye, entre otros campos, `entradas`, `salidas`, `total_personas`, `ocupacion_estimada_pct`, `hora_pico` y `es_fin_de_semana`.

### Vibracion: `SimuladorAcelerometro`

Los tramos se crean en `config.py` entre estaciones consecutivas. Por cada tramo se crean tres sensores, segun `SENSORES_POR_TRAMO`.

La vibracion se calcula usando:

- Fatiga base del tramo.
- Hora del dia.
- Cantidad estimada de pasajeros.
- Precipitacion.
- Variacion aleatoria del sensor.

Ejemplo:

```python
from Fuentes.accelerometer import SimuladorAcelerometro

simulador = SimuladorAcelerometro()
evento = simulador.generar_evento(pasajeros=500, precipitacion_mm=8)
lote = simulador.generar_lote(n=100, intervalo_seg=10)
```

Un evento incluye `vibracion_rms_mm_s2`, `frecuencia_hz`, `fatiga_acumulada`, `es_anomalia`, el tramo y el sensor que lo produjeron.

## 9. Archivos de salida

Para cada fecha de una generacion historica se crean:

```text
 datos_sinteticos/
 `-- YYYY-MM-DD/
     |-- clima_precipitacion.json
     |-- clima_precipitacion.csv
     |-- torniquetes_pasajeros.csv
     |-- torniquetes_pasajeros.ndjson
     |-- acelerometros_vibracion.json
     `-- acelerometros_vibracion.ndjson
```

El modo streaming crea:

```text
datos_streaming/streaming_YYYYMMDD_HHMMSS.json
```

Formatos:

- **JSON:** lista completa de diccionarios, legible por aplicaciones y librerias JSON.
- **CSV:** primera fila con nombres de campos y una fila por registro.
- **NDJSON:** un objeto JSON por linea, apropiado para procesamiento por eventos o grandes volumenes.

Los exportadores estan centralizados en `Persistencia/serializers.py`. Crean automaticamente las carpetas que no existan.

## 10. Identificadores y campos importantes

- `PAX-...`: evento de pasajeros.
- `VIB-...`: evento de vibracion.
- `CLIMA-...`: lectura del simulador climatico.
- `pluviometro_id`: identifica el pluviometro.
- `tramo_id`: identifica el tramo entre dos estaciones.
- `sensor_id`: identifica el acelerometro.
- `timestamp`: fecha y hora ISO 8601.
- `nivel_alerta`: `verde`, `amarilla`, `naranja` o `roja`.

El nombre `SimuladorSIATA` ya no se usa en la logica principal. `Fuentes/siata.py` conserva un alias para codigo antiguo:

```python
from Fuentes.siata import SimuladorSIATA
# Es el mismo tipo que SimuladorClima
```

Los archivos historicos existentes con nombres `siata_precipitacion.*` no se renombran automaticamente. Las nuevas ejecuciones generan `clima_precipitacion.*`.

## 11. Pruebas y validacion

Comprobar que los modulos compilan:

```powershell
python -m py_compile Fuentes\weather.py Fuentes\siata.py Fuentes\dataset.py Fuentes\streaming.py Fuentes\simuladores.py
```

Comprobar manualmente el fallback sin depender de internet:

```python
from datetime import datetime
from unittest.mock import patch
import requests
from Fuentes.weather import SimuladorClima

with patch(
    "Fuentes.weather.requests.get",
    side_effect=requests.exceptions.ConnectionError("sin red"),
):
    lectura = SimuladorClima().generar_lectura(timestamp=datetime.now())

print(lectura["precipitacion_mm_h"])
```

Para una validacion completa, ejecuta una generacion de un solo dia en una carpeta temporal o en una carpeta de prueba y comprueba que existan los seis archivos de salida.

## 12. Solucion de problemas

### `ModuleNotFoundError: No module named 'requests'`

Activa el entorno virtual e instala la dependencia:

```powershell
python -m pip install requests
```

### La API no responde

Es un caso soportado. `SimuladorClima` utiliza automaticamente datos sinteticos. Revisa que la lectura incluya `precipitacion_mm_h` y los demas campos climaticos.

### Se generaron demasiados datos

Reduce `dias` o aumenta los intervalos `intervalo_vibracion_seg`, `intervalo_pasajeros_min` e `intervalo_clima_min`.

### No aparecen los archivos

Asegurate de ejecutar el comando desde la raiz de `ProyectoMetro`. El programa imprime la ruta exacta de cada archivo exportado.

### Deseo conservar los datos antiguos

Usa un directorio de salida diferente, por ejemplo:

```powershell
python -c "from Ejecucion.dataset import generar_dataset_completo; generar_dataset_completo(dias=1, directorio_salida='datos_nueva_ejecucion')"
```

## 13. Flujo general

```text
Ejecucion/simuladores.py
        |
        +--> Ejecucion/dataset.py -------> datos_sinteticos/YYYY-MM-DD/
        |       |-- SimuladorTorniquetes
        |       |-- SimuladorAcelerometro
        |       `-- SimuladorClima --> Open-Meteo o fallback
        |
        `--> Ejecucion/streaming.py -----> datos_streaming/streaming_*.json
                |-- SimuladorTorniquetes
                |-- SimuladorAcelerometro
                `-- SimuladorClima
```

La separacion permite que cada modulo tenga una responsabilidad clara: los simuladores generan datos, `dataset.py` coordina la generacion historica, `streaming.py` coordina eventos continuos y `serializers.py` persiste los resultados.
