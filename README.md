# 🚀 Proyecto: Arbitraje Minorista

Este proyecto es una aplicación web diseñada para identificar oportunidades de **arbitraje minorista**. El sistema rastrea sitios de comercio electrónico, almacena los precios de los productos y los presenta en un dashboard para que el usuario pueda tomar decisiones de compra y reventa.

## 🏛️ Arquitectura General

El proyecto sigue una arquitectura moderna de tres componentes principales, diseñada para una clara separación de responsabilidades y escalabilidad.

1.  **Frontend (`/frontend`)**: Una Single Page Application (SPA) construida con **React** y **TypeScript**. Se encarga de toda la experiencia de usuario.
    -   **UI**: Material-UI (MUI).
    -   **Peticiones API**: `axios` y `@tanstack/react-query`.

2.  **Backend (`/backend`)**: Una API RESTful construida con **FastAPI** (Python). Orquesta toda la lógica de negocio, el web scraping y la comunicación con la base de datos.
    -   **Acceso a Datos**: SQLAlchemy.
    -   **Web Scraping**: Playwright.

3.  **Base de Datos (`/supabase`)**: Utilizamos **Supabase** como nuestro Backend as a Service (BaaS), principalmente por su base de datos **PostgreSQL** y su excelente CLI para la gestión de migraciones.

## ⚙️ Cómo Empezar: Guía de Desarrollo

A continuación se detallan los pasos y comandos para configurar y ejecutar el entorno de desarrollo local.

### Requisitos Previos

- **Node.js** (v18 o superior)
- **Python** (v3.10 o superior)
- **Supabase CLI** (`npm install -g supabase`)

### 1. Configuración del Backend

Navega al directorio del backend y activa el entorno virtual.

```bash
# 1. Navega al directorio del backend
cd backend

# 2. Crea y activa un entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate

# 3. Instala las dependencias
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Configura las variables de entorno
# Copia las variables de Supabase (URL, KEY, DATABASE_URL) a un archivo .env

# 5. Inicia el servidor de desarrollo
uvicorn main:app --reload --port 8080
```

El backend estará disponible en `http://localhost:8080`.

### 2. Configuración del Frontend

En una nueva terminal, navega al directorio del frontend.

```bash
# 1. Navega al directorio del frontend
cd frontend

# 2. Instala las dependencias
npm install

# 3. Inicia el servidor de desarrollo
npm start
```

La aplicación de React estará disponible en `http://localhost:3030`.

### 3. Gestión de la Base de Datos (Supabase)

Todas las migraciones del esquema de la base de datos se gestionan con la CLI de Supabase y se encuentran en la carpeta `/supabase/migrations`.

```bash
# Para aplicar las últimas migraciones a tu instancia local o en la nube
supabase db push
```

## ✅ Calidad y Testing

El proyecto está configurado con herramientas de calidad de código y testing para mantener un alto estándar.

- **Backend**: Ejecuta los tests con `pytest`.
- **Frontend**: Ejecuta los tests con `npm run test`.
- **Ambos**: Utilizan `pre-commit` hooks para formatear y "lintear" el código automáticamente antes de cada commit.