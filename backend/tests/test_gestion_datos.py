# backend/tests/test_gestion_datos.py

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.services.database import get_db, Base
from backend.routes.gestion_datos import (
    crear_minorista,
    MinoristaBase,
)  # Importar la función y el esquema
from backend.models.minorista import (
    Minorista as MinoristaModel,
)  # Importar el modelo ORM


@pytest.fixture(scope="function")
def direct_db_session_fixture():
    """
    Fixture que proporciona una sesión de BD aislada para llamadas directas a funciones.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield TestingSessionLocal

    app.dependency_overrides.clear()


# --- Test de Diagnóstico: Llamada Directa a la Función del Router ---


def test_crear_minorista_direct_call(direct_db_session_fixture):
    """
    Verifica la función crear_minorista directamente con una sesión de BD aislada.
    """
    Session = direct_db_session_fixture
    db = Session()
    try:
        # Verificar que la tabla está vacía al inicio
        initial_count = db.query(MinoristaModel).count()
        print(
            f"\n[DIAGNÓSTICO - Direct Call] Recuento inicial de minoristas: {initial_count}"
        )
        assert (
            initial_count == 0
        ), "La base de datos NO está vacía al iniciar el test directo."

        # Datos para el minorista
        minorista_data = MinoristaBase(
            nombre="Direct Test Minorista", url_base="https://direct.com"
        )

        # Llamar a la función del router directamente
        created_minorista = crear_minorista(minorista=minorista_data, db=db)

        # Verificar la respuesta
        assert created_minorista.nombre == "Direct Test Minorista"
        assert created_minorista.url_base == "https://direct.com/"
        assert created_minorista.id is not None

        # Verificar que el dato existe en la BD
        final_count = db.query(MinoristaModel).count()
        print(
            f"[DIAGNÓSTICO - Direct Call] Recuento final de minoristas: {final_count}"
        )
        assert (
            final_count == 1
        ), "El dato no se insertó correctamente en el test directo."

    finally:
        db.close()


# --- Test de API (para comparación) ---


@pytest.fixture(scope="function")
def api_client_fixture():
    """
    Fixture para tests de API, usando la misma lógica de BD aislada.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def test_crear_minorista_con_api_falla(api_client_fixture):
    """
    Este test de API debería fallar si el problema está en la interacción con FastAPI.
    """
    client = api_client_fixture
    response = client.post(
        "/gestion-datos/minoristas/",
        json={"nombre": "Test API", "url_base": "https://api.com"},
    )
    assert response.status_code == 201, response.text
