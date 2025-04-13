# Tourism Agent Webhook

## Descripción
Este proyecto implementa un webhook para procesar mensajes del agente de turismo, utilizando una arquitectura limpia (Clean Architecture) y siguiendo los principios SOLID y Domain-Driven Design (DDD).

## Estructura del Proyecto
El proyecto sigue una arquitectura por capas:

- **domain**: Contiene las entidades y reglas de negocio centrales
- **application**: Implementa la lógica de negocio y casos de uso
- **infrastructure**: Gestiona la interacción con servicios externos, bases de datos y configuración
- **presentation**: Maneja la exposición de API y endpoints
- **services**: Servicios auxiliares y utilidades

## Tecnologías Utilizadas
- FastAPI: Framework web de alto rendimiento
- Pydantic: Validación de datos y configuración
- Supabase: Base de datos y autenticación
- Gunicorn: Servidor WSGI para producción
- Docker: Containerización

## Requisitos
- Python 3.9+
- Docker (opcional para despliegue)

## Instalación

### Desarrollo Local
1. Clonar el repositorio:
   ```
   git clone https://github.com/dev-ai-automation/daxi.git
   cd daxi
   ```

2. Crear y activar entorno virtual:
   ```
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. Instalar dependencias:
   ```
   pip install -r requirements.txt
   ```

4. Configurar variables de entorno:
   ```
   cp .env.example .env
   # Editar .env con la configuración necesaria
   ```

5. Ejecutar la aplicación:
   ```
   uvicorn app.main:app --reload
   ```

### Despliegue con Docker
1. Construir la imagen:
   ```
   docker build -t tourism-agent-webhook .
   ```

2. Ejecutar el contenedor:
   ```
   docker run -p 8000:8000 --env-file .env tourism-agent-webhook
   ```

## Uso
Una vez en ejecución, la API estará disponible en:
- Documentación OpenAPI: http://localhost:8000/docs
- Documentación ReDoc: http://localhost:8000/redoc
- Endpoint de salud: http://localhost:8000/

## Licencia
MIT

## Contacto
Equipo de Soporte - soporte@ejemplo.com 