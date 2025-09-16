# Decisiones Técnicas del Proyecto

## Data Types Standardization

### Integer vs BigInteger
**Decisión**: Usar `Integer` en modelos SQLAlchemy para compatibilidad con SQLite en tests.

**Razón**:
- SQLite no maneja `BigInteger` autoincrement correctamente
- Para producción con PostgreSQL, se puede cambiar a `BigInteger` si se necesita
- Los tests pueden ejecutarse sin problemas

**Ubicación**:
- `backend/models/*.py` - Todos los IDs usan `Integer`
- `supabase/migrations/` - Las migraciones usan `BIGINT` para PostgreSQL

### Pydantic V2 Migration
**Decisión**: Migrar completamente a Pydantic V2 syntax.

**Cambios realizados**:
- `@validator` → `@field_validator` con `@classmethod`
- `orm_mode = True` → `model_config = ConfigDict(from_attributes=True)`

### FastAPI Lifecycle
**Decisión**: Migrar de `@app.on_event` a `lifespan` context manager.

**Razón**:
- `on_event` está deprecated en FastAPI
- `lifespan` permite mejor manejo de startup/shutdown
- Mejor control de tasks async

## Performance Optimizations

### Connection Pooling
- Pool size: 20 base + 30 overflow
- Pre-ping enabled para conexiones stale
- Recycle cada hora

### Concurrency
- Scraping concurrente con semáforos
- Batch processing para grandes volúmenes
- Event-driven architecture para desacoplamiento

## Observability

### Logging
- Structured JSON logging
- Correlation IDs para tracing
- Separate loggers por dominio (business, performance)

### Metrics
- In-memory metrics con TTL
- Counters y gauges con tags
- Health checks comprehensivos

### Monitoring Endpoints
- `/observability/health` - Health checks completos
- `/observability/metrics` - Métricas del sistema
- `/observability/ready` - Kubernetes readiness probe
- `/observability/live` - Kubernetes liveness probe