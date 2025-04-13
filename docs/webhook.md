# Webhook Implementation Guide

## Overview

El webhook implementado en este proyecto sigue una arquitectura de procesamiento asíncrono de mensajes, con autenticación HMAC para verificar la integridad y origen de las solicitudes. Es compatible con múltiples tipos de mensajes que permiten actualizar el estado de reservas, recibir datos de usuario y gestionar promociones. La implementación está optimizada para despliegue con Gunicorn y configuración de subdominios.

## Arquitectura Clean

El sistema de webhook sigue un patrón de diseño basado en eventos y está organizado según la Clean Architecture:

1. **Capa de Presentación**: La implementación del webhook está en `app/presentation/webhook/`
   - `routes.py`: Define los endpoints HTTP y maneja las solicitudes
   - `processors.py`: Procesa los mensajes recibidos de forma asíncrona

2. **Capa de Aplicación**: Contiene la lógica de negocio
   - Las herramientas para manejar fechas y reservas están en `app/application/services/tools/`

3. **Capa de Dominio**: Define los modelos de datos
   - Los modelos de mensajes están en `app/domain/entities/models/webhook_models.py`

4. **Capa de Infraestructura**: Maneja la interacción con servicios externos
   - La configuración está en `app/infrastructure/config/config/settings.py`
   - Los agentes conversacionales están en `app/infrastructure/external/agents/`
   - La persistencia está en `app/infrastructure/persistence/`

El flujo de datos es el siguiente:

```
[Sistema Externo] → [Gunicorn] → [Endpoints (presentation/webhook/routes.py)] → [Validación de firma] 
                                → [Procesadores (presentation/webhook/processors.py)] 
                                → [Agente (infrastructure/external/agents)]
                                → [Persistencia (infrastructure/persistence)]
```

## Implementación con Gunicorn

El webhook utiliza Gunicorn como servidor WSGI para producción, con las siguientes características:

- **Worker Class**: `uvicorn.workers.UvicornWorker` optimizado para FastAPI
- **Workers**: Configurables (recomendado 2*núcleos+1)
- **Threads**: Configurables para operaciones asíncronas
- **Configuración**: Definida en `gunicorn_config.py` en la raíz del proyecto

### Configuración de Gunicorn

```python
# gunicorn_config.py
import os
import multiprocessing

# Número de workers (procesos)
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
threads = int(os.getenv("GUNICORN_THREADS", "4"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
bind = os.getenv("GUNICORN_BIND", f"{os.getenv('WEBHOOK_HOST', '0.0.0.0')}:{os.getenv('WEBHOOK_PORT', '8000')}")
worker_class = "uvicorn.workers.UvicornWorker"
# ... otras configuraciones
```

## Implementación de Seguridad

### Autenticación HMAC

```python
# app/presentation/webhook/processors.py
def validate_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Valida la firma HMAC de un payload."""
    # Convertir secret a bytes si es string
    if isinstance(secret, str):
        secret = secret.encode()
        
    # Calcular hash HMAC utilizando SHA-256
    calculated_hmac = hmac.new(
        secret,
        payload,
        hashlib.sha256
    ).hexdigest()
    
    # Comparar firmas (comparación de tiempo constante)
    return hmac.compare_digest(calculated_hmac, signature)
```

La comparación usa `hmac.compare_digest()` para evitar ataques de timing que podrían comprometer la seguridad.

### Medidas Adicionales de Seguridad

1. **Rate Limiting**: Implementado por IP cliente con ventana deslizante
2. **Validación de Tamaño**: Restricción de tamaño máximo de payload (1MB)
3. **Procesamiento Asíncrono**: Evita bloqueos de servicio
4. **Logging Detallado**: Registra intentos de acceso no autorizados
5. **Aislamiento de Workers**: Gunicorn proporciona aislamiento entre procesos

## Configuración para Subdominios

El webhook está optimizado para ser servido bajo un subdominio específico mediante el uso de la variable `ROOT_PATH`. Esto permite que el webhook esté disponible en una URL como `https://webhook.midominio.com/api/webhook`.

### Configuración de FastAPI para Subdominios

```python
# app/main.py
app = FastAPI(
    title="Tourism Agent Webhook",
    description="Webhook para procesar mensajes del agente de turismo",
    version="1.0.0",
    root_path=os.getenv("ROOT_PATH", ""),  # Para configuración de subdominios
)
```

### Configuración de Proxy Inverso con NGINX

Para que funcione correctamente con un subdominio, es necesario configurar correctamente los encabezados HTTP en el proxy inverso:

```nginx
# Ejemplo de configuración Nginx para subdominio
server {
    listen 80;
    server_name webhook.midominio.com;

    location /api/webhook {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;
    }
}
```

## Modelos de Webhook

Los modelos de datos para el webhook están definidos en `app/domain/entities/models/webhook_models.py`:

```python
class WebhookMessage(BaseModel):
    """Modelo de mensaje recibido por el webhook"""
    type: str = Field(..., description="Tipo de mensaje recibido")
    content: str = Field(..., description="Contenido del mensaje")
    user_id: Optional[str] = Field(None, description="ID del usuario que envía el mensaje")
    timestamp: Optional[datetime] = Field(None, description="Timestamp del mensaje")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadatos adicionales")

class WebhookResponse(BaseModel):
    """Modelo de respuesta del webhook"""
    success: bool = Field(..., description="Indica si la operación fue exitosa")
    message: str = Field(..., description="Mensaje de la respuesta")
    data: Optional[Dict[str, Any]] = Field(None, description="Datos adicionales")
```

## Tipos de Mensajes Soportados

| Tipo | Descripción | Campos Requeridos |
|------|-------------|-------------------|
| `reservation_update` | Actualización de reserva | `reservation_id`, `status` |
| `promo` | Promoción o oferta | `promo_id`, `valid_until`, `discount` |
| `user_info` | Información de usuario | `user_id` (contenido libre) |

## Formato de Payload

```json
{
  "type": "reservation_update",
  "content": "La reservación ha sido confirmada",
  "user_id": "123456",
  "timestamp": "2023-11-12T15:30:45.123Z",
  "metadata": {
    "reservation_id": "res_abc123",
    "status": "confirmed"
  }
}
```

## Integración con Servicios Externos

El webhook está diseñado para integrarse con:

1. **Cal.com**: Para recibir actualizaciones de reservas (usando los tools en `app/application/services/tools/calendar_tools.py`)
2. **Supabase**: Para persistencia de datos (usando los servicios en `app/infrastructure/persistence/`)
3. **Sistemas de marketing**: Para campañas promocionales

## Guía de Uso para Clientes

Para enviar mensajes válidamente firmados al webhook:

1. Prepare el payload JSON según el formato especificado
2. Calcule la firma HMAC-SHA256 del payload usando la clave secreta compartida
3. Envíe una solicitud POST al endpoint correcto según la configuración de subdominio:
   - Default: `POST https://webhook.midominio.com/webhook/receive`
   - Con ROOT_PATH: `POST https://webhook.midominio.com/api/webhook/webhook/receive`
   - Headers requeridos:
     - `Content-Type: application/json`
     - `x-webhook-signature: <firma_calculada>`
   - Body: El payload JSON

### Ejemplo de Código (Python)

```python
import hmac
import hashlib
import json
import requests

def send_webhook(payload, secret, webhook_url):
    # Serializar payload a JSON
    payload_json = json.dumps(payload)
    
    # Calcular firma
    signature = hmac.new(
        secret.encode(),
        payload_json.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Enviar solicitud
    response = requests.post(
        webhook_url,
        headers={
            'Content-Type': 'application/json',
            'x-webhook-signature': signature
        },
        data=payload_json
    )
    
    return response.json()
```

## Consideraciones Técnicas

- **Idempotencia**: Los mensajes deben ser idempotentes para manejar reenvíos
- **Timeouts**: El procesamiento asíncrono respeta el timeout configurado en Gunicorn
- **Orden de Mensajes**: No se garantiza el procesamiento en orden estricto
- **Concurrencia**: El sistema está diseñado para manejar múltiples mensajes simultáneos mediante workers de Gunicorn

## Pruebas y Monitoreo

El webhook incluye un endpoint de health check para monitoring:
- Default: `/webhook/health`
- Con ROOT_PATH: `/api/webhook/webhook/health`

Los logs de actividad se escriben en:
- Logs de Gunicorn (acceso y error)
- Archivo de log (`app.log`)
- Supabase (para análisis histórico)

### Verificar Estado del Webhook

```bash
# Verificar estado de salud con configuración básica
curl https://webhook.midominio.com/webhook/health

# Verificar estado de salud con ROOT_PATH
curl https://webhook.midominio.com/api/webhook/webhook/health
```

## Optimizaciones de Rendimiento

- **Ajuste de Workers**: Configure `GUNICORN_WORKERS` según las capacidades de la máquina
- **Threads**: Ajuste `GUNICORN_THREADS` para operaciones I/O intensivas
- **Timeout**: Configure `GUNICORN_TIMEOUT` según la complejidad de procesamiento
- **Monitoreo**: Use herramientas como Prometheus para monitorear el rendimiento 

## Despliegue en GCP

Para desplegar el webhook en Google Cloud Platform, puede utilizar Cloud Run:

```bash
# Construir la imagen Docker
docker build -t webhook-service .

# Etiquetar para Container Registry
docker tag webhook-service gcr.io/[PROJECT-ID]/webhook-service

# Subir la imagen
docker push gcr.io/[PROJECT-ID]/webhook-service

# Desplegar en Cloud Run
gcloud run deploy webhook-service \
  --image gcr.io/[PROJECT-ID]/webhook-service \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --region us-central1 \
  --set-env-vars "WEBHOOK_SECRET=[SECRET],ROOT_PATH=/api"
``` 