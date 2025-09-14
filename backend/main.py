from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Arbitraje Minorista API",
    version="0.1.0",
    description="API para el seguimiento de productos y oportunidades de arbitraje."
)

# Configuración de CORS
origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API de Arbitraje Minorista"}

# Aquí se incluirán los routers más adelante
# from routes import productos
# app.include_router(productos.router)
