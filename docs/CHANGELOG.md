# 📝 CHANGELOG del Proyecto

Este documento registra los cambios significativos, decisiones y progreso del proyecto de Arbitraje Minorista.

---

## 🗓️ 15 de Septiembre, 2025 (Noche) - **FASE 3: Refinamiento y Documentación**

**Estado**: 🚧 **En Progreso**

Con las funcionalidades críticas y de observabilidad en su lugar, esta fase se enfoca en refinar la robustez del sistema y en formalizar la documentación para facilitar el mantenimiento y la escalabilidad a largo plazo.

### Logros Clave:

- **Automatizada la Adquisición de Datos con un Scheduler**:
  - **Qué**: Se ha implementado y activado el scheduler (`APScheduler`) que ejecuta el proceso de scraping de forma automática y periódica.
  - **Por qué**: Esto transforma la aplicación de una herramienta manual a un sistema de monitoreo autónomo. La recolección de datos ahora es constante y desatendida, asegurando que la información esté siempre actualizada.
  - **Cómo**: La función `scraping_job` ahora contiene la lógica para iterar sobre todos los minoristas activos, descubrir las URLs de sus productos y ejecutar el scraper para cada uno. El scheduler se inicia junto con la aplicación de FastAPI y ejecuta este trabajo cada 60 minutos.
  - **Referencia a Guía**: Cumple con la tarea de **Automatización** descrita en la Fase 2 del plan original del proyecto.

- **Finalizado y Probado el Servicio de Scraping (Corazón del Sistema)**:
  - **Qué**: Se ha refactorizado y probado exhaustivamente el servicio de scraping (`services/scraper.py`).
  - **Por qué**: El scraper es el componente más crítico y frágil del sistema. Sin pruebas automatizadas, cualquier cambio en la web de un minorista podría romper la recolección de datos de forma silenciosa. Ahora tenemos una red de seguridad que garantiza su fiabilidad.
  - **Cómo**:
    1.  Se refactorizó la función principal para desacoplar la lógica de extracción de la gestión del navegador, mejorando drásticamente la testeabilidad.
    2.  Se creó una suite de tests (`tests/test_scraper.py`) que incluye un test unitario para el endpoint y tests de integración para el servicio.
    3.  Las pruebas usan `Playwright` para cargar HTML de prueba y verifican tanto el caso de éxito (extracción correcta) como los casos de error (ej. un selector no encontrado).
  - **Referencia a Guía**: Cumple con las secciones **#8 (TDD)** y **#9 (Calidad Mínima)**, aplicando pruebas a la lógica de negocio más importante.

- **Implementada Validación de Datos a Nivel de Base de Datos (Capa 1)**:
  - **Qué**: Se ha añadido una nueva migración que introduce `CHECK constraints` directamente en las tablas `productos`, `historial_precios` y `minoristas`.
  - **Por qué**: Esto crea una red de seguridad fundamental para la integridad de los datos. Asegura que datos inválidos (como precios negativos) no puedan ser insertados en el sistema, sin importar desde dónde se origine la petición. Es la primera y más fuerte de las 3 capas de validación.
  - **Cómo**: Se usó `ALTER TABLE ... ADD CONSTRAINT` para añadir reglas que verifican que los precios sean positivos y que los nombres de los minoristas no estén vacíos.
  - **Referencia a Guía**: Implementa la **Capa 1** de la **Sección #28 (Three-Layer Validation Strategy)**.

---

## 🗓️ 15 de Septiembre, 2025 (Tarde) - **FASE 2: Observabilidad y Robustez Funcional**

**Estado**: ✅ **Completada**

Iniciamos la segunda fase de desarrollo, centrada en implementar las funcionalidades críticas y las capacidades de monitoreo que nos permitirán operar con confianza.

### Logros Clave:

- **Implementado el Patrón de Catálogo para Minoristas**:
  - **Qué**: Se ha añadido un nuevo endpoint `GET /gestion-datos/minoristas/buscar` a la API.
  - **Por qué**: Para mejorar la usabilidad y eficiencia del frontend. Este endpoint permite realizar búsquedas dinámicas de minoristas, lo que es esencial para implementar funcionalidades como campos de autocompletado, en lugar de tener que cargar la lista completa de minoristas.
  - **Cómo**: El nuevo endpoint acepta un parámetro de consulta `q` y devuelve una lista de minoristas cuyo nombre coincide con el término de búsqueda (insensible a mayúsculas/minúsculas).
  - **Referencia a Guía**: Implementa la recomendación de la **Sección #23 (Catálogos Pattern - Autocompletado)**.

- **Implementada la Base para Pruebas Automatizadas en el Frontend**:
  - **Qué**: Se ha configurado el entorno de pruebas para el frontend utilizando `Jest` y `React Testing Library`. Se creó el primer test para el componente `FormularioMinorista.tsx`.
  - **Por qué**: Esta era la **carencia más crítica** detectada en el análisis inicial. Sin pruebas en el frontend, no tenemos red de seguridad contra regresiones o bugs al modificar la interfaz. Esta adición es un pilar fundamental para garantizar la calidad y la mantenibilidad de la aplicación.
  - **Cómo**:
    - Se añadieron las dependencias de desarrollo (`jest`, `@testing-library/react`, etc.) al `package.json`.
    - Se crearon los archivos de configuración `jest.config.js` y `src/setupTests.ts`.
    - Se escribió un test inicial (`FormularioMinorista.test.tsx`) que valida el renderizado y la interacción básica del formulario.
    - Se añadió un script `npm run test` para ejecutar la suite de pruebas.
  - **Referencia a Guía**: Aborda directamente las secciones **#8 (TDD)** y **#9 (Cobertura y Calidad Mínimas)**.

- **Añadidos Índices Estratégicos en la Base de Datos**:
  - **Qué**: Se ha creado y aplicado una nueva migración (`..._add_strategic_indexes.sql`) que añade índices a las columnas `id_minorista` en `productos`, y a `id_producto`, `fecha_registro` y `id_minorista` en `historial_precios`.
  - **Por qué**: La performance de las consultas es crítica para el éxito de la aplicación. La tabla `historial_precios` crecerá de forma masiva, y sin estos índices, las consultas para obtener el historial de un producto se volverían progresivamente más lentas, degradando la experiencia de usuario y la eficiencia del sistema.
  - **Cómo**: Se han añadido índices B-tree simples y un índice compuesto (`id_producto`, `fecha_registro DESC`) para optimizar las operaciones de filtrado y ordenación más comunes, siguiendo las mejores prácticas para el diseño de esquemas de bases de datos relacionales.
  - **Referencia a Guía**: Esta acción aborda directamente la **Sección #20 (Índices Estratégicos & Query Optimization)**, una de las de mayor impacto según la guía.

- **Implementado Endpoint de Monitoreo (`/health`)**:
  - **Qué**: Se ha añadido un nuevo endpoint a la API (`/health`) que realiza un chequeo de salud de los servicios críticos del sistema.
  - **Por qué**: Esto es fundamental para la **observabilidad** del sistema. Nos permite verificar de forma automática y remota si la aplicación está funcionando correctamente, empezando por su componente más vital: la base de datos.
  - **Cómo**:
    - Se creó un `HealthChecker` en `backend/core/monitoring.py` que contiene la lógica para verificar la conexión y velocidad de respuesta de la base de datos Supabase.
    - Se expuso esta lógica a través de una nueva ruta en `backend/routes/monitoring.py`.
    - El endpoint devuelve un estado `200 OK` si todo funciona, o un `503 Service Unavailable` si un componente crítico ha fallado, facilitando la integración con sistemas de monitoreo automatizado en el futuro.
  - **Referencia a Guía**: Esta implementación sigue las directrices de la **Sección #19 (Performance Monitoring & Health Checks)** del documento de mejores prácticas.

---

## 🗓️ 15 de Septiembre, 2025 - **FASE 1: Cimientos de Calidad y Robustez**

**Estado**: ✅ **Completada**

Se ha finalizado con éxito la implementación de una base de código robusta, profesional y automatizada, aplicando las directrices del documento `00_guia_mejores_practicas.md`. Este esfuerzo sienta las bases para un desarrollo futuro rápido y seguro.

### Logros Clave por Componente:

#### **Backend (`/backend`)**

- **Calidad de Código Automatizada**: Se ha integrado un sistema de `pre-commit` que ejecuta `black` (formateador) y `ruff` (linter) antes de cada commit. Esto garantiza que todo el código que se sube al repositorio es consistente, limpio y sigue las mejores prácticas de Python.
- **Estructura de Código Mejorada**: Se consolidaron las rutas de la API para eliminar redundancia y se creó un archivo `.gitignore` específico para el backend, previniendo la subida de archivos sensibles o innecesarios (`.env`, `__pycache__`).
- **Integración Continua (CI)**: Se ha implementado un workflow en GitHub Actions (`.github/workflows/ci-backend.yml`). Este "guardián" valida automáticamente la calidad del código en cada `push` y `pull_request`, asegurando la integridad de la rama principal.

#### **Frontend (`/frontend`)**

- **Calidad de Código Automatizada**: Se ha integrado `prettier` (formateador) con `eslint` (linter) para mantener un estándar de código consistente en todo el proyecto de React y TypeScript.
- **Configuración de Entorno**: Se ha externalizado la URL de la API a un archivo `.env.development`, eliminando URLs "hardcodeadas" y facilitando el cambio entre entornos de desarrollo y producción.
- **Scripts de Mantenimiento**: Se añadieron los scripts `lint` y `format` al `package.json`, permitiendo a cualquier desarrollador verificar y arreglar fácilmente el estilo del código.

### Próximos Pasos Definidos:

Se ha delineado el plan para la Fase 2, enfocado en la funcionalidad y observabilidad del sistema:

- **Tarea 2.1**: Manejo de Errores Centralizado (Backend).
- **Tarea 2.2**: Logging Estructurado (Backend).
- **Tarea 2.3**: Suite de Tests Inicial (Backend).
