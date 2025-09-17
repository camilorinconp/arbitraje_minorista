#!/usr/bin/env python3
"""
Database restore script for Arbitraje Minorista.
Usage: python restore.py --backup-file=path/to/backup.sql [--target-db=new_db_name]
"""

import asyncio
import os
import sys
import argparse
import subprocess
import gzip
from pathlib import Path
import logging

# Add backend to path for imports
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from core.config import settings

logger = logging.getLogger(__name__)


class DatabaseRestore:
    """
    Database restore utility with safety checks.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url

    async def restore_backup(self, backup_path: Path, target_db: str = None, confirm_destructive: bool = False) -> bool:
        """
        Restore database from backup file.
        """
        if not backup_path.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return False

        # Parse database URL
        db_params = self._parse_database_url(self.database_url)
        if target_db:
            db_params["database"] = target_db

        logger.info(f"Restoring backup to database: {db_params['database']}")

        # Safety check for production
        if not confirm_destructive and db_params["database"] in ["arbitraje_prod", "arbitraje_production"]:
            logger.error("Refusing to restore to production database without explicit confirmation")
            logger.error("Use --confirm-destructive flag if you really want to do this")
            return False

        try:
            # Create database if it doesn't exist (for new restores)
            if target_db:
                await self._create_database_if_not_exists(db_params, target_db)

            # Determine if backup is compressed
            is_compressed = backup_path.suffix == ".gz"

            # Build pg_restore command
            if is_compressed or backup_path.suffix == ".dump":
                cmd = [
                    "pg_restore",
                    "--host", db_params["host"],
                    "--port", str(db_params["port"]),
                    "--username", db_params["user"],
                    "--dbname", db_params["database"],
                    "--verbose",
                    "--no-password",
                    "--clean",  # Drop existing objects first
                    "--if-exists",  # Don't error if objects don't exist
                    str(backup_path)
                ]
            else:
                # Plain SQL file
                cmd = [
                    "psql",
                    "--host", db_params["host"],
                    "--port", str(db_params["port"]),
                    "--username", db_params["user"],
                    "--dbname", db_params["database"],
                    "--no-password",
                    "--file", str(backup_path)
                ]

            # Set environment variables
            env = os.environ.copy()
            env["PGPASSWORD"] = db_params["password"]

            # Execute restore command
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )

            logger.info("Database restore completed successfully")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Restore failed: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during restore: {e}")
            return False

    async def _create_database_if_not_exists(self, db_params: dict, database_name: str):
        """Create database if it doesn't exist."""
        # Connect to postgres database to create new database
        temp_params = db_params.copy()
        temp_params["database"] = "postgres"

        cmd = [
            "psql",
            "--host", temp_params["host"],
            "--port", str(temp_params["port"]),
            "--username", temp_params["user"],
            "--dbname", temp_params["database"],
            "--no-password",
            "--command", f"CREATE DATABASE {database_name};"
        ]

        env = os.environ.copy()
        env["PGPASSWORD"] = temp_params["password"]

        try:
            subprocess.run(cmd, env=env, capture_output=True, check=True)
            logger.info(f"Created database: {database_name}")
        except subprocess.CalledProcessError:
            # Database might already exist, that's okay
            logger.info(f"Database {database_name} already exists or creation failed")

    def _parse_database_url(self, url: str) -> dict:
        """Parse PostgreSQL URL into components."""
        # Remove postgresql:// or postgresql+asyncpg:// prefix
        url = url.replace("postgresql+asyncpg://", "").replace("postgresql://", "")

        # Split into parts
        if "@" in url:
            auth_part, host_part = url.split("@", 1)
            if ":" in auth_part:
                user, password = auth_part.split(":", 1)
            else:
                user, password = auth_part, ""
        else:
            raise ValueError("Invalid database URL format")

        if "/" in host_part:
            host_port, database = host_part.split("/", 1)
        else:
            raise ValueError("Invalid database URL format")

        if ":" in host_port:
            host, port = host_port.split(":", 1)
        else:
            host, port = host_port, "5432"

        return {
            "user": user,
            "password": password,
            "host": host,
            "port": int(port),
            "database": database
        }

    async def validate_backup(self, backup_path: Path) -> bool:
        """
        Validate backup file before attempting restore.
        """
        logger.info(f"Validating backup file: {backup_path}")

        if not backup_path.exists():
            logger.error("Backup file does not exist")
            return False

        if backup_path.stat().st_size == 0:
            logger.error("Backup file is empty")
            return False

        # Check file format
        try:
            if backup_path.suffix == ".gz":
                with gzip.open(backup_path, 'rt') as f:
                    first_line = f.readline()
            else:
                with open(backup_path, 'r') as f:
                    first_line = f.readline()

            if "PostgreSQL database dump" in first_line or "PGDMP" in first_line:
                logger.info("Backup file validation passed")
                return True
            else:
                logger.error("File does not appear to be a valid PostgreSQL backup")
                return False

        except Exception as e:
            logger.error(f"Error validating backup file: {e}")
            return False

    async def test_restore(self, backup_path: Path) -> bool:
        """
        Test restore to a temporary database.
        """
        test_db_name = f"arbitraje_restore_test_{int(asyncio.get_event_loop().time())}"

        logger.info(f"Testing restore to temporary database: {test_db_name}")

        try:
            # Perform test restore
            success = await self.restore_backup(backup_path, target_db=test_db_name)

            if success:
                logger.info("Test restore successful")

                # Cleanup test database
                await self._drop_database(test_db_name)
                logger.info(f"Cleaned up test database: {test_db_name}")

            return success

        except Exception as e:
            logger.error(f"Test restore failed: {e}")
            # Try to cleanup even if restore failed
            try:
                await self._drop_database(test_db_name)
            except:
                pass
            return False

    async def _drop_database(self, database_name: str):
        """Drop a database."""
        db_params = self._parse_database_url(self.database_url)
        db_params["database"] = "postgres"  # Connect to postgres to drop database

        cmd = [
            "psql",
            "--host", db_params["host"],
            "--port", str(db_params["port"]),
            "--username", db_params["user"],
            "--dbname", db_params["database"],
            "--no-password",
            "--command", f"DROP DATABASE IF EXISTS {database_name};"
        ]

        env = os.environ.copy()
        env["PGPASSWORD"] = db_params["password"]

        subprocess.run(cmd, env=env, capture_output=True, check=True)


async def main():
    parser = argparse.ArgumentParser(description='Database restore utility')
    parser.add_argument('--backup-file', required=True, help='Path to backup file')
    parser.add_argument('--target-db', help='Target database name (creates new if specified)')
    parser.add_argument('--database-url', help='Database URL (overrides settings)')
    parser.add_argument('--test-only', action='store_true', help='Test restore without affecting main database')
    parser.add_argument('--validate-only', action='store_true', help='Only validate backup file')
    parser.add_argument('--confirm-destructive', action='store_true',
                        help='Confirm destructive operation on production database')

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Get database URL
    database_url = args.database_url or settings.database_url
    if not database_url:
        logger.error("No database URL provided. Set DATABASE_URL or use --database-url")
        sys.exit(1)

    backup_path = Path(args.backup_file)
    restore_tool = DatabaseRestore(database_url)

    try:
        # Validate backup file
        if not await restore_tool.validate_backup(backup_path):
            logger.error("Backup validation failed")
            sys.exit(1)

        if args.validate_only:
            logger.info("Backup validation successful")
            return

        # Test restore if requested
        if args.test_only:
            if await restore_tool.test_restore(backup_path):
                logger.info("Test restore successful")
            else:
                logger.error("Test restore failed")
                sys.exit(1)
            return

        # Perform actual restore
        success = await restore_tool.restore_backup(
            backup_path,
            target_db=args.target_db,
            confirm_destructive=args.confirm_destructive
        )

        if success:
            logger.info("Database restore completed successfully")
        else:
            logger.error("Database restore failed")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Restore operation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())