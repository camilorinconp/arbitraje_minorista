# 🚀 Guía de Despliegue del Proyecto Arbitraje Minorista

Este documento detalla los pasos y consideraciones para desplegar la aplicación de Arbitraje Minorista en un entorno de producción. La arquitectura se compone de un Backend (FastAPI), un Frontend (React) y una Base de Datos (Supabase).

## 1. Consideraciones Generales

*   **Variables de Entorno:** Todas las credenciales y configuraciones sensibles (URLs de API, claves de Supabase, etc.) deben gestionarse mediante variables de entorno en el servicio de hosting.
*   **HTTPS:** Para producción, siempre utiliza HTTPS. La mayoría de los proveedores de hosting lo configuran automáticamente.
*   **Dominio:** Configura tu dominio personalizado si es necesario.

## 2. Despliegue del Backend (FastAPI)

El backend de FastAPI es una aplicación Python que puede desplegarse en plataformas que soporten aplicaciones web Python (ej. Render, Heroku, AWS EC2, Google Cloud Run, DigitalOcean Droplets).

### 2.1. Preparación

1.  **`requirements.txt`:** Asegúrate de que tu archivo `backend/requirements.txt` contenga todas las dependencias necesarias para producción. Es buena práctica usar `pip freeze > requirements.txt` en tu entorno virtual de producción.
2.  **Variables de Entorno:** Configura las siguientes variables en tu proveedor de hosting:
    *   `SUPABASE_URL`: URL de tu proyecto Supabase.
    *   `SUPABASE_KEY`: Clave `anon` o `service_role` de tu proyecto Supabase (dependiendo de tus políticas de seguridad).
    *   `DATABASE_URL`: URL de conexión directa a tu base de datos PostgreSQL de Supabase (formato `postgresql://user:password@host:port/database`).

### 2.2. Proceso de Despliegue

El proceso general implica:

1.  **Clonar el Repositorio:** El proveedor de hosting clonará tu repositorio Git.
2.  **Instalar Dependencias:** Ejecutará `pip install -r requirements.txt`.
3.  **Ejecutar la Aplicación:** El comando para iniciar la aplicación será similar a:
    ```bash
    uvicorn backend.main:app --host 0.0.0.0 --port $PORT
    ```
    *   `--host 0.0.0.0`: Permite que la aplicación sea accesible desde cualquier IP (necesario en entornos de servidor).
    *   `--port $PORT`: Utiliza la variable de entorno `$PORT` proporcionada por el servicio de hosting.

### 2.3. Consideraciones Adicionales

*   **Scheduler (APScheduler):** Si tu plataforma de despliegue no mantiene los procesos en segundo plano de forma persistente (ej. algunos servicios serverless), el scheduler de APScheduler podría no funcionar continuamente. En estos casos, considera:
    *   **Servicios de Cron:** Usar un servicio de cron externo (ej. Cronjob de tu proveedor cloud, GitHub Actions con un `workflow_dispatch`) para disparar el endpoint `/scraper/run/` periódicamente.
    *   **Servidor Dedicado:** Desplegar en un servidor virtual (VM) donde puedas controlar el proceso de Uvicorn y asegurar que el scheduler se mantenga activo.
*   **Migraciones de Base de Datos:** Las migraciones de Supabase (`supabase db push`) deben ejecutarse manualmente o como parte de un paso de CI/CD antes del despliegue, para asegurar que el esquema de la base de datos esté actualizado.

## 3. Despliegue del Frontend (React)

El frontend de React es una aplicación de una sola página (SPA) que se compila en archivos estáticos (HTML, CSS, JavaScript). Puede desplegarse en cualquier servicio de hosting de archivos estáticos (ej. Vercel, Netlify, GitHub Pages, AWS S3 + CloudFront).

### 3.1. Preparación

1.  **`package.json`:** Asegúrate de que todas las dependencias de producción estén listadas.
2.  **Variables de Entorno:** Configura la siguiente variable en tu proveedor de hosting:
    *   `REACT_APP_API_BASE_URL`: La URL pública de tu backend de FastAPI desplegado (ej. `https://api.tudominio.com`).

### 3.2. Proceso de Despliegue

1.  **Instalar Dependencias:** El proveedor de hosting ejecutará `npm install`.
2.  **Compilar la Aplicación:** Ejecutará `npm run build`. Esto creará una carpeta `build` con los archivos estáticos optimizados.
3.  **Servir Archivos Estáticos:** El proveedor de hosting servirá el contenido de la carpeta `build`.

## 4. Gestión de la Base de Datos (Supabase)

Supabase gestiona su propia infraestructura de base de datos. No necesitas desplegar la base de datos por separado. Sin embargo, es crucial:

*   **Aplicar Migraciones:** Antes de cada despliegue importante, asegúrate de que todas las migraciones de la base de datos (`supabase/migrations/`) hayan sido aplicadas a tu instancia de Supabase en producción usando `supabase db push`.
*   **Políticas de Seguridad (RLS):** Revisa y configura las políticas de Row Level Security (RLS) en Supabase para controlar el acceso a tus datos de forma segura.
