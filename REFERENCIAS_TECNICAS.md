# Referencias Técnicas - Sistema de Navegación Automática

## 🗺️ Mapa de Archivos Clave

### 🔐 Sistema de Autenticación

#### Backend
- **`backend/auth_simple.py:184-225`** - Endpoint `/auth/me` con datos reales de BD
- **`backend/auth_simple.py:73-140`** - Endpoint `/auth/register` con persistencia JSON
- **`backend/auth_simple.py:141-183`** - Endpoint `/auth/login` con JWT tokens
- **`backend/users_simple.json:9,18`** - Usuarios admin con permisos completos

#### Frontend
- **`frontend/src/contexts/AuthContext.tsx:44-49`** - Mapeo de permisos por rol
- **`frontend/src/contexts/AuthContext.tsx:101-120`** - Registro con auto-login
- **`frontend/src/api/authApi.ts:64-70`** - Almacenamiento de tokens con expires_in
- **`frontend/src/components/auth/RegisterForm.tsx:109`** - Mensaje de confirmación

### 🏪 Gestión de Minoristas

#### Backend CRUD Completo
- **`backend/main_simple.py:79-83`** - GET listar minoristas
- **`backend/main_simple.py:85-116`** - POST crear minorista
- **`backend/main_simple.py:152-200`** - PUT actualizar minorista
- **`backend/main_simple.py:118-150`** - DELETE eliminar minorista
- **`backend/minoristas_simple.json`** - Persistencia de datos

#### Frontend UI Completa
- **`frontend/src/pages/GestionMinoristas.tsx:140-142`** - Integración onEdit/onDelete
- **`frontend/src/components/ListaMinoristas.tsx:83-96`** - Botones editar/eliminar
- **`frontend/src/api/gestionDatosApi.ts:119-121`** - API PUT para actualizaciones
- **`frontend/src/api/gestionDatosApi.ts:130-132`** - API DELETE para eliminaciones

### 🌐 Navegación y Permisos

#### Rutas Protegidas
- **`frontend/src/App.tsx:59-67`** - Ruta `/minoristas` con WriteRoute
- **`frontend/src/components/layout/Navbar.tsx:106-115`** - Botón Minoristas con hasPermission('write')
- **`frontend/src/components/auth/ProtectedRoute.tsx`** - Componente de protección

#### Sistema de Roles
- **`frontend/src/contexts/AuthContext.tsx:156-163`** - Función hasPermission()
- **`frontend/src/contexts/AuthContext.tsx:148-151`** - Función hasRole()

## 🔧 Configuración de Servicios

### Backend (Puerto 8080)
```bash
# Comando actual ejecutándose
cd /Users/user/arbitraje_minorista/backend
source venv/bin/activate
uvicorn main_simple:app --reload --host 0.0.0.0 --port 8080
```

### Frontend (Puerto 3030)
```bash
# Comando actual ejecutándose
cd /Users/user/arbitraje_minorista/frontend
BROWSER=none PORT=3030 npm start
```

## 🐛 Resolución de Problemas Comunes

### Problema: Botones no aparecen en UI
- **Archivo**: `backend/users_simple.json:9,18`
- **Solución**: Verificar que role sea "admin" o "scraper"
- **Comando verificación**: `curl http://localhost:8080/auth/me`

### Problema: Error 405 Method Not Allowed
- **Archivos**: `backend/main_simple.py:85-200`
- **Verificación**: Confirmar que endpoints POST, PUT, DELETE estén implementados

### Problema: Error de CORS
- **Archivo**: `backend/main_simple.py:10-16`
- **Config**: `allow_origins=["http://localhost:3030"]`

## 📊 Endpoints API Disponibles

### Autenticación
```
POST /auth/register     # Registro usuarios
POST /auth/login        # Login con JWT
GET  /auth/me          # Info usuario actual
GET  /health           # Health check
```

### Minoristas
```
GET    /gestion-datos/minoristas/     # Listar
POST   /gestion-datos/minoristas/     # Crear
PUT    /gestion-datos/minoristas/{id} # Editar
DELETE /gestion-datos/minoristas/{id} # Eliminar
```

## 🎯 Testing Rápido

### Verificar Backend
```bash
# Test endpoints desde terminal
curl http://localhost:8080/health
curl http://localhost:8080/gestion-datos/minoristas/
curl http://localhost:8080/auth/me
```

### Verificar Frontend
1. **URL**: http://localhost:3030
2. **Login**: camilo.rincon.pineda@gmail.com / cualquier password
3. **Navegación**: Verificar que aparezca botón "Minoristas"
4. **CRUD**: Probar crear/editar/eliminar minoristas

## 🔄 Flujo de Desarrollo

### Para agregar nueva funcionalidad:
1. **Backend**: Agregar endpoint en `main_simple.py`
2. **API**: Agregar función en `gestionDatosApi.ts`
3. **UI**: Crear componente en `src/components/`
4. **Ruta**: Agregar en `App.tsx` si necesario
5. **Navegación**: Actualizar `Navbar.tsx` si necesario

### Para debugging:
1. **Logs Backend**: Revisar terminal del uvicorn
2. **Logs Frontend**: Abrir DevTools → Console
3. **Network**: DevTools → Network para ver APIs calls
4. **Estado**: React DevTools para context/state

---

**Nota**: Este archivo sirve como mapa de navegación rápida para el desarrollo y mantenimiento del sistema.