# backend/core/monitoring.py

import time
from typing import Dict, Any
from supabase import Client

from ..services.database import supabase_client


class HealthChecker:
    """
    Clase que encapsula las verificaciones de salud de los componentes del sistema.
    """

    @staticmethod
    async def check_database(db_client: Client) -> Dict[str, Any]:
        """
        Verifica la conectividad y respuesta de la base de datos de Supabase.
        Realiza una consulta simple y mide el tiempo de respuesta.
        """
        start_time = time.time()
        try:
            # Usamos una tabla que sabemos que existe, como 'minoristas' de una migración anterior.
            # Si no existe, la consulta fallará, lo cual es un indicador de salud válido.
            db_client.table("minoristas").select("id").limit(1).execute()

            db_time = round((time.time() - start_time) * 1000, 2)

            return {
                "status": "healthy",
                "response_time_ms": db_time,
                "details": "Conexión y consulta a la base de datos exitosa.",
            }
        except Exception as e:
            db_time = round((time.time() - start_time) * 1000, 2)
            return {
                "status": "unhealthy",
                "response_time_ms": db_time,
                "details": f"Error al conectar o consultar la base de datos: {str(e)}",
            }

    @classmethod
    async def run_checks(cls) -> Dict[str, Any]:
        """
        Ejecuta todas las verificaciones de salud y devuelve un reporte consolidado.
        """
        checks = {"database": await cls.check_database(supabase_client)}

        overall_status = "healthy"
        for component_check in checks.values():
            if component_check["status"] == "unhealthy":
                overall_status = "unhealthy"
                break

        return {
            "overall_status": overall_status,
            "timestamp": time.time(),
            "checks": checks,
        }
