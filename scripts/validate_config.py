#!/usr/bin/env python3
"""
Script para validar configuración antes del deployment.
Uso: python scripts/validate_config.py [environment]
"""

import os
import sys
from pathlib import Path

# Añadir backend al path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from core.config import Settings, validate_production_config, get_environment_info


def validate_environment_config(env: str = None):
    """Validar configuración para un entorno específico."""

    if env:
        env_file = f".env.{env}"
        if os.path.exists(env_file):
            print(f"✓ Usando archivo de configuración: {env_file}")
            os.environ["APP_ENV"] = env
            # Cargar variables del archivo usando python-dotenv
            from dotenv import load_dotenv
            load_dotenv(env_file, override=True)
        else:
            print(f"⚠️  Archivo {env_file} no encontrado")

    try:
        settings = Settings()
        print(f"✓ Configuración cargada correctamente")

        # Mostrar información del entorno
        print("\n=== INFORMACIÓN DEL ENTORNO ===")
        env_info = get_environment_info()
        for key, value in env_info.items():
            print(f"{key}: {value}")

        # Validar configuración de producción
        if settings.is_production:
            print("\n=== VALIDACIÓN DE PRODUCCIÓN ===")
            errors = validate_production_config()
            if errors:
                print("❌ Errores de configuración encontrados:")
                for error in errors:
                    print(f"  - {error}")
                return False
            else:
                print("✓ Configuración de producción válida")

        # Validaciones adicionales
        print("\n=== VALIDACIONES ADICIONALES ===")

        # Verificar conexión a base de datos
        print(f"Base de datos: {settings.database_url_for_env}")
        if "sqlite" in settings.database_url_for_env and settings.is_production:
            print("⚠️  SQLite no recomendado para producción")

        # Verificar configuración de rate limiting
        print(f"Rate limiting: {settings.redis_url_for_rate_limiting}")
        if settings.is_production and "memory" in settings.redis_url_for_rate_limiting:
            print("⚠️  Rate limiting en memoria no recomendado para producción")

        # Verificar configuración de cache
        cache_url = settings.redis_url_for_cache
        print(f"Cache: {'Redis' if cache_url else 'Memory'}")
        if settings.is_production and not cache_url:
            print("⚠️  Cache en memoria no recomendado para producción")

        # Verificar CORS
        cors_origins = settings.get_cors_origins_for_env()
        print(f"CORS origins: {cors_origins}")
        if settings.is_production:
            localhost_origins = [o for o in cors_origins if "localhost" in o or "127.0.0.1" in o]
            if localhost_origins:
                print(f"⚠️  Origins de localhost en producción: {localhost_origins}")

        # Verificar configuración de scraping
        print(f"Scraping concurrent: {settings.scraper_max_concurrent}")
        print(f"Scraping timeout: {settings.scraper_default_timeout}s")

        # Verificar configuración de scheduler
        print(f"Scheduler: {'Enabled' if settings.scheduler_enabled else 'Disabled'}")
        if settings.scheduler_enabled:
            print(f"Scraping interval: {settings.scheduler_scraping_interval}s")

        print("\n✓ Validación completada exitosamente")
        return True

    except Exception as e:
        print(f"❌ Error al cargar configuración: {e}")
        return False


def main():
    """Función principal."""
    import argparse

    parser = argparse.ArgumentParser(description="Validar configuración de la aplicación")
    parser.add_argument("environment", nargs="?",
                       choices=["development", "staging", "production"],
                       help="Entorno a validar")
    parser.add_argument("--check-secrets", action="store_true",
                       help="Verificar que los secrets estén configurados")

    args = parser.parse_args()

    print("=== VALIDADOR DE CONFIGURACIÓN ===")

    if args.environment:
        print(f"Validando configuración para: {args.environment}")
    else:
        print("Validando configuración actual")

    success = validate_environment_config(args.environment)

    if args.check_secrets and args.environment == "production":
        print("\n=== VERIFICACIÓN DE SECRETS ===")
        required_secrets = [
            "SECRET_KEY",
            "DATABASE_URL",
            "SUPABASE_URL",
            "SUPABASE_SERVICE_ROLE_KEY"
        ]

        missing_secrets = []
        for secret in required_secrets:
            if not os.getenv(secret) or os.getenv(secret) in ["change-me", "your-key-here"]:
                missing_secrets.append(secret)

        if missing_secrets:
            print(f"❌ Secrets faltantes o con valores por defecto: {missing_secrets}")
            success = False
        else:
            print("✓ Todos los secrets requeridos están configurados")

    if success:
        print("\n🎉 Configuración válida para deployment")
        sys.exit(0)
    else:
        print("\n💥 Configuración inválida - corregir errores antes del deployment")
        sys.exit(1)


if __name__ == "__main__":
    main()