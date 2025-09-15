# 📝 CHANGELOG del Proyecto

Este documento registra los cambios significativos, decisiones y progreso del proyecto de Arbitraje Minorista.

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
