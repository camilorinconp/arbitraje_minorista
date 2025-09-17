# Simple main.py for testing authentication

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json
import os
from datetime import datetime

# Create FastAPI app
app = FastAPI(title="Arbitraje Minorista API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3030"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include simple auth routes
try:
    from auth_simple import router as auth_router
    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    print("✅ Simple auth routes loaded successfully")
except Exception as e:
    print(f"❌ Error loading auth routes: {e}")

@app.get("/")
async def root():
    return {"message": "Arbitraje Minorista API - Authentication Service"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "auth"}

# Pydantic models for minoristas
class MinoristaBase(BaseModel):
    nombre: str
    url_base: str
    activo: Optional[bool] = True
    name_selector: Optional[str] = None
    price_selector: Optional[str] = None
    image_selector: Optional[str] = None
    discovery_url: Optional[str] = None
    product_link_selector: Optional[str] = None

class Minorista(MinoristaBase):
    id: int
    created_at: str
    updated_at: Optional[str] = None

# File paths
MINORISTAS_FILE = "minoristas_simple.json"

def load_minoristas():
    """Load minoristas from JSON file"""
    if os.path.exists(MINORISTAS_FILE):
        try:
            with open(MINORISTAS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"minoristas": [], "next_id": 1}

def save_minoristas(data):
    """Save minoristas to JSON file"""
    with open(MINORISTAS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# Basic endpoints for dashboard
@app.get("/gestion-datos/productos/")
async def get_productos():
    """Get productos - returns array directly as expected by frontend"""
    return []

@app.get("/gestion-datos/minoristas/")
async def get_minoristas():
    """Get minoristas - returns array directly as expected by frontend"""
    data = load_minoristas()
    return data["minoristas"]

@app.post("/gestion-datos/minoristas/")
async def create_minorista(minorista_data: MinoristaBase):
    """Create a new minorista"""
    try:
        # Load existing data
        data = load_minoristas()

        # Create new minorista
        new_minorista = {
            "id": data["next_id"],
            "nombre": minorista_data.nombre,
            "url_base": minorista_data.url_base,
            "activo": minorista_data.activo,
            "name_selector": minorista_data.name_selector,
            "price_selector": minorista_data.price_selector,
            "image_selector": minorista_data.image_selector,
            "discovery_url": minorista_data.discovery_url,
            "product_link_selector": minorista_data.product_link_selector,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": None
        }

        # Add to list and save
        data["minoristas"].append(new_minorista)
        data["next_id"] += 1
        save_minoristas(data)

        return new_minorista

    except Exception as e:
        print(f"Error creating minorista: {e}")
        raise

@app.delete("/gestion-datos/minoristas/{minorista_id}")
async def delete_minorista(minorista_id: int):
    """Delete a minorista by ID"""
    try:
        # Load existing data
        data = load_minoristas()

        # Find minorista by ID
        minorista_to_delete = None
        for i, minorista in enumerate(data["minoristas"]):
            if minorista["id"] == minorista_id:
                minorista_to_delete = data["minoristas"].pop(i)
                break

        if not minorista_to_delete:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Minorista con ID {minorista_id} no encontrado"
            )

        # Save updated data
        save_minoristas(data)

        return {"message": f"Minorista '{minorista_to_delete['nombre']}' eliminado exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting minorista: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al eliminar minorista"
        )

@app.put("/gestion-datos/minoristas/{minorista_id}")
async def update_minorista(minorista_id: int, minorista_data: MinoristaBase):
    """Update a minorista by ID"""
    try:
        # Load existing data
        data = load_minoristas()

        # Find minorista by ID
        minorista_index = None
        for i, minorista in enumerate(data["minoristas"]):
            if minorista["id"] == minorista_id:
                minorista_index = i
                break

        if minorista_index is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Minorista con ID {minorista_id} no encontrado"
            )

        # Update minorista data
        updated_minorista = {
            "id": minorista_id,
            "nombre": minorista_data.nombre,
            "url_base": minorista_data.url_base,
            "activo": minorista_data.activo,
            "name_selector": minorista_data.name_selector,
            "price_selector": minorista_data.price_selector,
            "image_selector": minorista_data.image_selector,
            "discovery_url": minorista_data.discovery_url,
            "product_link_selector": minorista_data.product_link_selector,
            "created_at": data["minoristas"][minorista_index]["created_at"],  # Keep original
            "updated_at": datetime.utcnow().isoformat()
        }

        # Replace in array
        data["minoristas"][minorista_index] = updated_minorista
        save_minoristas(data)

        return updated_minorista

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating minorista: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al actualizar minorista"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)