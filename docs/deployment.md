# Guía de Despliegue en Google Cloud Platform (GCP)

Esta guía detalla el proceso para desplegar la aplicación con Gunicorn en Google Cloud Platform, utilizando Cloud Run para el servicio de webhook.

## Requisitos Previos

1. Cuenta de Google Cloud Platform
2. Google Cloud SDK instalado y configurado localmente
3. Docker instalado en la máquina local
4. Acceso a Container Registry o Artifact Registry en GCP

## Pasos para el Despliegue

### 1. Configuración Inicial del Proyecto GCP

```bash
# Iniciar sesión en GCP
gcloud auth login

# Configurar el proyecto
gcloud config set project [ID-DEL-PROYECTO]

# Habilitar APIs necesarias
gcloud services enable cloudbuild.googleapis.com run.googleapis.com \
  containerregistry.googleapis.com artifactregistry.googleapis.com
```

### 2. Preparar Variables de Entorno para Producción

Crea un archivo `.env.prod` con las variables de entorno para producción:

#Cuando cree el repo hacerle un git.ignore en las variables de ambiente
#Investigar la forma en cloud con variables de ambiente

```
# Configuración de webhook y seguridad
WEBHOOK_SECRET=tu_clave_secreta_para_produccion
WEBHOOK_PORT=8080
WEBHOOK_HOST=0.0.0.0

# Configuración para Cal.com y Supabase
CALCOM_API_KEY=tu_api_key_de_calcom
CALCOM_EVENT_TYPE_ID=tu_event_type_id
CALCOM_USERNAME=tu_username
CALCOM_USEREMAIL=tu_email
SUPABASE_URL=tu_url_de_supabase
SUPABASE_KEY=tu_key_de_supabase

# Configuración de Gunicorn
GUNICORN_WORKERS=4
GUNICORN_THREADS=2
GUNICORN_TIMEOUT=120
GUNICORN_LOG_LEVEL=info

# Configuración para subdominios
ROOT_PATH=/api/webhook
DOMAIN=midominio.com
SUBDOMAIN=webhook

# Entorno
ENVIRONMENT=production
```

### 3. Construir la Imagen Docker

```bash
# Construir la imagen localmente
docker build -t tourism-agent-webhook .

# Etiquetar la imagen para Container Registry
docker tag tourism-agent-webhook gcr.io/[ID-DEL-PROYECTO]/tourism-agent-webhook:latest

# Subir la imagen a Container Registry
docker push gcr.io/[ID-DEL-PROYECTO]/tourism-agent-webhook:latest
```

### 4. Desplegar en Cloud Run

#### Opción 1: Mediante línea de comandos

```bash
gcloud run deploy tourism-agent \
  --image gcr.io/[ID-DEL-PROYECTO]/tourism-agent-webhook:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --env-vars-file .env.prod
```

#### Opción 2: Desde la consola de GCP

1. Ve a la [Consola de Google Cloud](https://console.cloud.google.com/)
2. Navega a **Cloud Run**
3. Haz clic en **Crear servicio**
4. Selecciona la imagen de Container Registry
5. Configura las opciones:
   - Memoria: 512Mi
   - Puerto: 8080
   - Variables de entorno: Añade todas las de `.env.prod`
   - Autenticación: Permitir invocaciones no autenticadas
6. Haz clic en **Crear**

### 5. Configurar Subdominio

#### Opción 1: Usando Cloud Run con dominio mapeado

1. Ve a **Cloud Run** en la consola
2. Selecciona el servicio desplegado
3. Ve a la pestaña **Dominios**
4. Haz clic en **Añadir asignación**
5. Introduce el subdominio completo (ej. `webhook.midominio.com`)
6. Sigue las instrucciones para verificar y configurar tu dominio

#### Opción 2: Usando Nginx como proxy inverso

Si estás utilizando un servidor Nginx como proxy, configura un bloque de servidor para el subdominio:

```nginx
server {
    listen 80;
    server_name webhook.midominio.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;
    }
}
```

#### Opción 3: Usando un balanceador de carga HTTP(S) de GCP

1. Crea un balanceador de carga HTTP(S)
2. Configura un mapa de URL para dirigir el tráfico a tu servicio Cloud Run
3. Configura el certificado SSL para tu dominio
4. Apunta el DNS de tu subdominio al balanceador de carga

### 6. Pruebas de Configuración del Subdominio

Comprueba que el subdominio está correctamente configurado con:

```bash
# Verificar redirección y respuesta del servidor
curl -v https://webhook.tudominio.com/webhook/health

# Verificar que ROOT_PATH está correctamente configurado
curl -v https://webhook.tudominio.com/api/webhook/health
```

### 7. Configurar Secretos de Manera Segura (Recomendado)

Para mayor seguridad, utiliza Secret Manager para almacenar variables sensibles:

```bash
# Crear secreto para el webhook
echo -n "tu_clave_secreta_para_produccion" | \
  gcloud secrets create webhook-secret --data-file=-

# Otorgar acceso a Cloud Run
gcloud secrets add-iam-policy-binding webhook-secret \
  --member="serviceAccount:service-[NUMERO-DE-PROYECTO]@serverless-robot-prod.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

Luego actualiza el servicio para usar el secreto:

```bash
gcloud run services update tourism-agent \
  --update-secrets=WEBHOOK_SECRET=webhook-secret:latest
```

### 8. Configurar Cloud Scheduler para Health Checks (Recomendado)

Para mantener activo el servicio y realizar verificaciones de salud periódicas:

```bash
gcloud scheduler jobs create http webhook-health-check \
  --schedule="*/15 * * * *" \
  --uri="https://webhook.tudominio.com/api/webhook/health" \
  --http-method=GET \
  --attempt-deadline=30s
```

## Monitoreo y Gestión del Servidor Gunicorn

### Comandos para Supervisar Gunicorn

#### Ver logs del servidor

```bash
# En Cloud Run, usar Cloud Logging
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=tourism-agent" --limit=10

# En servidor propio
tail -f /var/log/gunicorn/error.log
tail -f /var/log/gunicorn/access.log
```

#### Verificar procesos de Gunicorn

```bash
# Ver procesos de gunicorn en ejecución
ps aux | grep gunicorn

# Verificar puertos en uso
netstat -tulpn | grep 8000
```

### Configuración de Rendimiento

Para ajustar el rendimiento de Gunicorn, modifica estas variables:

- `GUNICORN_WORKERS`: Generalmente se recomienda `2 * núcleos + 1`
- `GUNICORN_THREADS`: Para aplicaciones con operaciones asíncronas, aumentar este valor
- `GUNICORN_TIMEOUT`: Tiempo máximo de procesamiento de una solicitud

Ejemplo de ajuste para una máquina de 4 núcleos:

```
GUNICORN_WORKERS=9
GUNICORN_THREADS=4
GUNICORN_TIMEOUT=120
```

## Solución de Problemas

### Error de Subdominio No Funciona

Si el subdominio no funciona correctamente:

1. Verificar que el DNS esté configurado correctamente:
   ```bash
   dig webhook.tudominio.com
   ```

2. Comprobar la variable `ROOT_PATH` está configurada adecuadamente

3. Verificar los logs de Gunicorn para errores de enrutamiento:
   ```bash
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=tourism-agent AND textPayload:ROOT_PATH" --limit=10
   ```

### Error de Memoria Insuficiente

Si el servicio se cierra por falta de memoria, ajusta la configuración:

```bash
gcloud run services update tourism-agent --memory 1Gi

# Y reduce el número de workers
--update-env-vars GUNICORN_WORKERS=2
```

### Timeout en Solicitudes

Cloud Run tiene un límite de 60 segundos para las solicitudes. Para operaciones largas, considera:
- Implementar procesamientos asíncronos
- Utilizar Cloud Tasks para operaciones en segundo plano
- Ajustar `GUNICORN_TIMEOUT` a un valor menor que el timeout de Cloud Run

### Limitaciones en Conexiones Activas

Si recibes muchas solicitudes simultáneas, ajusta la configuración de concurrencia:

```bash
gcloud run services update tourism-agent --concurrency 80
--update-env-vars GUNICORN_WORKERS=4,GUNICORN_THREADS=8
```

## Optimizaciones Adicionales

- **SSL Termination**: Configura Gunicorn para terminar SSL, o mejor utiliza un proxy como Nginx
- **Cacheo**: Configura Cloud CDN para contenido estático
- **Worker Class**: Usa el worker `uvicorn.workers.UvicornWorker` para mejor rendimiento con FastAPI
- **Monitorización**: Configura herramientas como Prometheus para monitorización avanzada
- **Región**: Elige la región más cercana a tus usuarios 