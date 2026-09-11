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

En este proyecto ya quedaron validados estos valores reales:

| Dato | Valor actual | Uso |
|---|---|---|
| ID del proyecto GCP | `terraform-demo-metro` | Identifica el proyecto de Google Cloud. |
| Tema de vibración | `tema-metro-vibracion` | Recibe eventos de acelerómetros. |
| Tema de pasajeros | `tema-metro-pasajeros` | Recibe eventos de torniquetes. |
| Tema de clima | `tema-metro-clima` | Recibe lecturas de precipitación. |
| Credenciales locales | `gcloud auth application-default login` | Permite autenticar el programa sin JSON. |

Los nombres de los topics no llevan el sufijo `-sub`; ese sufijo pertenece a las suscripciones de BigQuery.

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

## 5. Autenticación local recomendada

Para este proyecto, la forma funcional y valida fue usar la autenticación por defecto de Google Cloud en tu cuenta local, en lugar de un JSON de cuenta de servicio.

```powershell
gcloud auth login
gcloud auth application-default login
gcloud config set project terraform-demo-metro
```

Con esto, Python y la librería `google-cloud-pubsub` pueden autenticarse usando Application Default Credentials (ADC) sin necesidad de crear o mantener un archivo `cuenta-servicio.json`.

> Si tu administrador bloqueó la descarga de claves JSON, esta es la opción recomendada y ya quedó verificada.

## 6. Configurar proyecto y temas

En la misma sesión de PowerShell, define las variables que lee el código:

```powershell
[System.Environment]::SetEnvironmentVariable("GCP_PROJECT_ID", "terraform-demo-metro", "Process")
[System.Environment]::SetEnvironmentVariable("GCP_TOPIC_VIBRACION", "tema-metro-vibracion", "Process")
[System.Environment]::SetEnvironmentVariable("GCP_TOPIC_PASAJEROS", "tema-metro-pasajeros", "Process")
[System.Environment]::SetEnvironmentVariable("GCP_TOPIC_CLIMA", "tema-metro-clima", "Process")
```

Si quieres dejar estas variables guardadas para futuras sesiones, puedes usar `"User"` en lugar de `"Process"`.

Verifica que estén definidas:

```powershell
[System.Environment]::GetEnvironmentVariable("GCP_PROJECT_ID", "Process")
[System.Environment]::GetEnvironmentVariable("GCP_TOPIC_VIBRACION", "Process")
[System.Environment]::GetEnvironmentVariable("GCP_TOPIC_PASAJEROS", "Process")
[System.Environment]::GetEnvironmentVariable("GCP_TOPIC_CLIMA", "Process")
```

No agregues estos valores como claves dentro del código si el repositorio será público. Los nombres de temas no son secretos, pero mantenerlos como configuración facilita cambiar de proyecto.

## 9. Ejecutar el publicador

Desde la carpeta raíz `ProyectoMetro`:

```powershell
python -m Integraciones.publicador_gcp
```

La ejecución ya quedó verificada con este proyecto. La salida esperada es similar a:

```text
Enviado clima -> ID GCP: 21778070818337697
Enviado vibracion -> ID GCP: 21778451765662594
Enviado pasajeros -> ID GCP: 21778288952457217
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

Por defecto, el publicador funciona durante 60 segundos con un intervalo de un segundo. Puedes cambiar esos valores en la misma sesión:

```powershell
[System.Environment]::SetEnvironmentVariable("GCP_DURACION_SEG", "120", "Process")
[System.Environment]::SetEnvironmentVariable("GCP_INTERVALO_SEG", "0.5", "Process")
python -m Integraciones.publicador_gcp
```

Para una prueba corta:

```powershell
[System.Environment]::SetEnvironmentVariable("GCP_DURACION_SEG", "10", "Process")
[System.Environment]::SetEnvironmentVariable("GCP_INTERVALO_SEG", "1", "Process")
python -m Integraciones.publicador_gcp
```

Detén la ejecución antes de tiempo con `Ctrl+C`.

## 11. Verificar que los mensajes llegan

Para esta configuración ya existen las subscriptions de BigQuery:

- `sub-metro-vib-bq`
- `sub-metro-pass-bq`
- `sub-metro-clima-bq`

Puedes comprobar los mensajes con una suscripción temporal o directamente revisando que las subscriptions ya están recibiendo datos.

```bash
gcloud pubsub subscriptions pull sub-metro-clima-bq --limit=5 --auto-ack --project=terraform-demo-metro
```

Repite el procedimiento para pasajeros y vibración cambiando el nombre de la subscription:

```bash
gcloud pubsub subscriptions pull sub-metro-pass-bq --limit=5 --auto-ack --project=terraform-demo-metro
gcloud pubsub subscriptions pull sub-metro-vib-bq --limit=5 --auto-ack --project=terraform-demo-metro
```

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

Con la configuración actual del proyecto, la forma recomendada es autenticarse con `gcloud auth application-default login` y luego ejecutar el script. Si quieres verificar la autenticación en local:

```powershell
gcloud auth application-default print-access-token
```

Si el comando devuelve un token, entonces las credenciales por defecto quedaron configuradas correctamente.

### Permiso denegado

La cuenta de servicio debe tener el rol `Pub/Sub Publisher`. Revisa también que los temas pertenezcan al proyecto indicado en `GCP_PROJECT_ID`.

### El tema no existe

Los nombres configurados deben coincidir exactamente con los temas creados en Pub/Sub. El publicador no crea temas automáticamente.

### `google-cloud-pubsub` no está instalado

Ejecuta:

```powershell
python -m pip install google-cloud-pubsub
```

### El proyecto no es el correcto

Si `gcloud pubsub topics list` falla con un proyecto number, entonces debes usar el `PROJECT_ID`, no el `PROJECT_NUMBER`.

```powershell
gcloud projects list
```

Y luego usa el valor de `PROJECT_ID` en la configuración (`terraform-demo-metro` en este caso).

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
