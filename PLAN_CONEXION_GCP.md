# Plan de conexión con Google Cloud Pub/Sub

Este documento describe cómo conectar el proyecto Metro con Google Cloud Pub/Sub usando el publicador ubicado en `Integraciones/publicador_gcp.py`.

El flujo será:

```text
Simuladores Python
        |
        v
Integraciones/publicador_gcp.py
        |
        +--> Tema Pub/Sub de vibración
        +--> Tema Pub/Sub de pasajeros
        `--> Tema Pub/Sub de clima
```

## 1. Datos que debes definir

Antes de ejecutar el código, define estos valores:

| Dato | Ejemplo | Uso |
|---|---|---|
| ID del proyecto GCP | `metro-datos-123` | Identifica el proyecto de Google Cloud. |
| Tema de vibración | `tema-metro-vibracion` | Recibe eventos de acelerómetros. |
| Tema de pasajeros | `tema-metro-pasajeros` | Recibe eventos de torniquetes. |
| Tema de clima | `tema-metro-clima` | Recibe lecturas de precipitación. |
| Archivo de credenciales | `cuenta-servicio.json` | Permite autenticar el programa fuera de GCP. |

Los nombres son ejemplos. Debes reemplazarlos con los valores reales de tu proyecto.

## 2. Crear o seleccionar el proyecto de GCP

1. Entra a [Google Cloud Console](https://console.cloud.google.com/).
2. Crea un proyecto nuevo o selecciona uno existente.
3. Copia el **ID del proyecto**, no solamente el nombre visible.
4. Conserva ese valor para `GCP_PROJECT_ID`.

El ID suele tener un formato parecido a:

```text
metro-datos-123456
```

## 3. Activar la API de Pub/Sub

En Google Cloud Console:

1. Abre **APIs y servicios**.
2. Selecciona **Biblioteca**.
3. Busca **Pub/Sub API**.
4. Presiona **Habilitar**.

También puedes hacerlo desde Cloud Shell:

```bash
gcloud services enable pubsub.googleapis.com --project=TU_PROJECT_ID
```

Reemplaza `TU_PROJECT_ID` por el ID real del proyecto.

## 4. Crear los tres temas

Crea estos tres temas en Pub/Sub:

```text
tema-metro-vibracion
tema-metro-pasajeros
tema-metro-clima
```

Desde Cloud Shell:

```bash
gcloud pubsub topics create tema-metro-vibracion --project=TU_PROJECT_ID
gcloud pubsub topics create tema-metro-pasajeros --project=TU_PROJECT_ID
gcloud pubsub topics create tema-metro-clima --project=TU_PROJECT_ID
```

El código no crea los temas automáticamente. Deben existir antes de ejecutar `Integraciones/publicador_gcp.py`.

## 5. Crear una cuenta de servicio

Si ejecutarás Python desde tu computador, crea una cuenta de servicio:

1. Ve a **IAM y administración**.
2. Entra a **Cuentas de servicio**.
3. Selecciona **Crear cuenta de servicio**.
4. Asígnale un nombre, por ejemplo `publicador-metro`.
5. Asigna el rol **Pub/Sub Publisher**.
6. Finaliza la creación.

El permiso mínimo necesario es publicar mensajes en los tres temas. Evita usar permisos de propietario o editor si no son necesarios.

## 6. Crear la clave de la cuenta de servicio

Dentro de la cuenta de servicio:

1. Abre la pestaña **Claves**.
2. Selecciona **Agregar clave**.
3. Elige **Crear clave nueva**.
4. Selecciona formato **JSON**.
5. Descarga el archivo en una ubicación segura.

No cambies el contenido de la clave y no la subas a GitHub. Google solo permite descargarla una vez; si se expone, revócala y crea otra.

## 7. Configurar autenticación en Windows

Instala la librería desde PowerShell, en la raíz del proyecto:

```powershell
python -m pip install google-cloud-pubsub
```

Indica la ruta de la clave descargada:

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\ruta\segura\publicador-metro.json"
```

La variable solo queda configurada en la sesión actual de PowerShell. Para confirmar que existe sin mostrar el contenido de la clave:

```powershell
Test-Path $env:GOOGLE_APPLICATION_CREDENTIALS
```

El resultado esperado es:

```text
True
```

## 8. Configurar proyecto y temas

En la misma sesión de PowerShell, define las variables que lee el código:

```powershell
$env:GCP_PROJECT_ID = "TU_PROJECT_ID"
$env:GCP_TOPIC_VIBRACION = "tema-metro-vibracion"
$env:GCP_TOPIC_PASAJEROS = "tema-metro-pasajeros"
$env:GCP_TOPIC_CLIMA = "tema-metro-clima"
```

Verifica que estén definidas:

```powershell
$env:GCP_PROJECT_ID
$env:GCP_TOPIC_VIBRACION
$env:GCP_TOPIC_PASAJEROS
$env:GCP_TOPIC_CLIMA
```

No agregues estos valores como claves dentro del código si el repositorio será público. Los nombres de temas no son secretos, pero mantenerlos como configuración facilita cambiar de proyecto.

## 9. Ejecutar el publicador

Desde la carpeta raíz `ProyectoMetro`:

```powershell
python -m Integraciones.publicador_gcp
```

El programa:

1. Crea los simuladores de vibración, pasajeros y clima.
2. Selecciona un tipo de evento según los pesos configurados.
3. Genera el evento con el simulador correspondiente.
4. Lo convierte a JSON y luego a bytes UTF-8.
5. Lo envía al tema Pub/Sub correspondiente.
6. Espera la confirmación y muestra el ID del mensaje.

La salida esperada se parece a:

```text
Enviado vibracion -> ID GCP: 1234567890123456
Enviado pasajeros -> ID GCP: 1234567890123457
Enviado clima -> ID GCP: 1234567890123458
```

## 10. Controlar duración e intervalo

Por defecto, el publicador funciona durante 60 segundos con un intervalo de un segundo. Puedes cambiar esos valores:

```powershell
$env:GCP_DURACION_SEG = "120"
$env:GCP_INTERVALO_SEG = "0.5"
python -m Integraciones.publicador_gcp
```

Para una prueba corta:

```powershell
$env:GCP_DURACION_SEG = "10"
$env:GCP_INTERVALO_SEG = "1"
python -m Integraciones.publicador_gcp
```

Detén la ejecución antes de tiempo con `Ctrl+C`.

## 11. Verificar que los mensajes llegan

Puedes comprobar los mensajes creando suscripciones temporales. Una suscripción permite leer los mensajes publicados en un tema.

```bash
gcloud pubsub subscriptions create prueba-vibracion \
  --topic=tema-metro-vibracion \
  --project=TU_PROJECT_ID

gcloud pubsub subscriptions pull prueba-vibracion \
  --limit=5 \
  --auto-ack \
  --project=TU_PROJECT_ID
```

Repite el procedimiento para pasajeros y clima cambiando el nombre del tema y la suscripción.

Una lectura climática debe contener campos como:

```json
{
  "lectura_id": "CLIMA-202609031200-PLV-001",
  "pluviometro_id": "PLV-001",
  "timestamp": "2026-09-03T12:00:00",
  "precipitacion_mm_h": 4.2,
  "precipitacion_acumulada_dia_mm": 18.0,
  "nivel_alerta": "verde",
  "esta_lloviendo": true
}
```

## 12. Errores frecuentes

### Falta una variable de entorno

Mensaje esperado:

```text
Faltan variables de entorno para Pub/Sub: GCP_PROJECT_ID, ...
```

Solución: define las cuatro variables `GCP_*` de la sección 8.

### No se encuentran las credenciales

Verifica:

```powershell
Test-Path $env:GOOGLE_APPLICATION_CREDENTIALS
```

La ruta debe apuntar al archivo JSON descargado de Google Cloud.

### Permiso denegado

La cuenta de servicio debe tener el rol `Pub/Sub Publisher`. Revisa también que los temas pertenezcan al proyecto indicado en `GCP_PROJECT_ID`.

### El tema no existe

Los nombres configurados deben coincidir exactamente con los temas creados en Pub/Sub. El publicador no crea temas automáticamente.

### `google-cloud-pubsub` no está instalado

Ejecuta:

```powershell
python -m pip install google-cloud-pubsub
```

## 13. Lista de comprobación

Antes de ejecutar en un entorno real, confirma:

- [ ] Existe el proyecto de GCP.
- [ ] Está habilitada la Pub/Sub API.
- [ ] Existen los tres temas.
- [ ] Existe la cuenta de servicio.
- [ ] La cuenta tiene el rol `Pub/Sub Publisher`.
- [ ] La clave JSON está fuera del repositorio.
- [ ] `GOOGLE_APPLICATION_CREDENTIALS` apunta a la clave correcta.
- [ ] `GCP_PROJECT_ID` contiene el ID real del proyecto.
- [ ] Los tres nombres `GCP_TOPIC_*` coinciden con los temas.
- [ ] Está instalada la librería `google-cloud-pubsub`.
- [ ] Se verificó la llegada de mensajes mediante una suscripción.

## 14. Siguiente paso: BigQuery

Pub/Sub recibe los mensajes, pero no los guarda automáticamente en BigQuery. Para almacenarlos se debe crear posteriormente una suscripción de BigQuery por tema o implementar un consumidor que transforme y cargue los mensajes en las tablas `clima`, `torniquetes_pasajeros` y `vibracion`.

La separación recomendada es:

```text
tema-metro-clima       -> tabla clima
tema-metro-pasajeros   -> tabla torniquetes_pasajeros
tema-metro-vibracion   -> tabla vibracion
```
