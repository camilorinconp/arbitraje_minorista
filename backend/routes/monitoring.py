# backend/routes/monitoring.py

from fastapi import APIRouter, Response, status

from ..core.monitoring import HealthChecker

router = APIRouter(
    prefix="/health",
    tags=["Monitoring"],
)

@router.get("/", summary="Realiza un chequeo de salud completo del sistema")
async def health_check(response: Response):
    """
    Endpoint de chequeo de salud.

    Verifica el estado de todos los componentes críticos del sistema (ej. Base de Datos)
    y devuelve un reporte detallado.

    - **200 OK**: Si todos los sistemas están saludables.
    - **503 Service Unavailable**: Si algún sistema crítico no está saludable.
    """
    health_report = await HealthChecker.run_checks()
    
    if health_report["overall_status"] == "unhealthy":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return health_report
