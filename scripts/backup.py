#!/usr/bin/env python3
"""
Automated backup script for Arbitraje Minorista database.
Usage: python backup.py [--environment=production] [--compress] [--upload-s3]
"""

import asyncio
import asyncpg
import os
import sys
import argparse
import subprocess
import gzip
import shutil
from datetime import datetime, timezone
from pathlib import Path
import logging
import boto3
from botocore.exceptions import ClientError

# Add backend to path for imports
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from core.config import settings

logger = logging.getLogger(__name__)


class DatabaseBackup:
    """
    Database backup utility with compression and cloud storage support.
    """

    def __init__(self, database_url: str, backup_dir: str = "backups"):
        self.database_url = database_url
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)

    async def create_backup(self, compress: bool = True, include_data: bool = True) -> Path:
        """
        Create database backup using pg_dump.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_filename = f"arbitraje_backup_{timestamp}.sql"
        backup_path = self.backup_dir / backup_filename

        logger.info(f"Creating backup: {backup_path}")

        # Parse database URL
        db_params = self._parse_database_url(self.database_url)

        # Build pg_dump command
        cmd = [
            "pg_dump",
            "--host", db_params["host"],
            "--port", str(db_params["port"]),
            "--username", db_params["user"],
            "--dbname", db_params["database"],
            "--verbose",
            "--no-password",  # Use PGPASSWORD environment variable
            "--format", "custom" if compress else "plain",
            "--file", str(backup_path)
        ]

        if not include_data:
            cmd.append("--schema-only")

        # Set environment variables for pg_dump
        env = os.environ.copy()
        env["PGPASSWORD"] = db_params["password"]

        try:
            # Execute pg_dump
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )

            logger.info(f"Backup created successfully: {backup_path}")

            # Compress if requested and not already compressed
            if compress and backup_path.suffix != ".dump":
                compressed_path = self._compress_backup(backup_path)
                backup_path.unlink()  # Remove uncompressed file
                backup_path = compressed_path

            return backup_path

        except subprocess.CalledProcessError as e:
            logger.error(f"Backup failed: {e.stderr}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during backup: {e}")
            raise

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

    def _compress_backup(self, backup_path: Path) -> Path:
        """Compress backup file using gzip."""
        compressed_path = backup_path.with_suffix(backup_path.suffix + ".gz")

        logger.info(f"Compressing backup: {compressed_path}")

        with open(backup_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        logger.info(f"Backup compressed: {compressed_path}")
        return compressed_path

    async def upload_to_s3(self, backup_path: Path, bucket: str, key_prefix: str = "backups/") -> str:
        """
        Upload backup file to S3.
        """
        s3_key = f"{key_prefix}{backup_path.name}"

        logger.info(f"Uploading backup to S3: s3://{bucket}/{s3_key}")

        try:
            s3_client = boto3.client('s3')

            # Upload file
            s3_client.upload_file(
                str(backup_path),
                bucket,
                s3_key,
                ExtraArgs={
                    'StorageClass': 'STANDARD_IA',  # Cheaper storage for backups
                    'Metadata': {
                        'created_at': datetime.now(timezone.utc).isoformat(),
                        'database': 'arbitraje_minorista',
                        'backup_type': 'automated'
                    }
                }
            )

            logger.info(f"Backup uploaded successfully: s3://{bucket}/{s3_key}")
            return f"s3://{bucket}/{s3_key}"

        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during S3 upload: {e}")
            raise

    def cleanup_old_backups(self, retention_days: int = 30):
        """
        Remove backups older than retention_days.
        """
        cutoff_time = datetime.now(timezone.utc).timestamp() - (retention_days * 24 * 3600)

        logger.info(f"Cleaning up backups older than {retention_days} days")

        removed_count = 0
        for backup_file in self.backup_dir.glob("arbitraje_backup_*.sql*"):
            if backup_file.stat().st_mtime < cutoff_time:
                logger.info(f"Removing old backup: {backup_file}")
                backup_file.unlink()
                removed_count += 1

        logger.info(f"Removed {removed_count} old backup files")

    async def verify_backup(self, backup_path: Path) -> bool:
        """
        Verify backup integrity by attempting to restore to a test database.
        """
        logger.info(f"Verifying backup: {backup_path}")

        # This would require a test database setup
        # For now, just check file size and format
        if not backup_path.exists():
            logger.error("Backup file does not exist")
            return False

        if backup_path.stat().st_size == 0:
            logger.error("Backup file is empty")
            return False

        # Check if it's a valid backup format
        try:
            if backup_path.suffix == ".gz":
                with gzip.open(backup_path, 'rt') as f:
                    first_line = f.readline()
            else:
                with open(backup_path, 'r') as f:
                    first_line = f.readline()

            if "PostgreSQL database dump" in first_line or "PGDMP" in first_line:
                logger.info("Backup verification passed")
                return True
            else:
                logger.error("Backup file does not appear to be a valid PostgreSQL dump")
                return False

        except Exception as e:
            logger.error(f"Error verifying backup: {e}")
            return False

    def get_backup_info(self) -> dict:
        """
        Get information about existing backups.
        """
        backups = []
        total_size = 0

        for backup_file in sorted(self.backup_dir.glob("arbitraje_backup_*.sql*")):
            stat = backup_file.stat()
            backups.append({
                "filename": backup_file.name,
                "path": str(backup_file),
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / 1024 / 1024, 2),
                "created_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
            })
            total_size += stat.st_size

        return {
            "backup_directory": str(self.backup_dir),
            "total_backups": len(backups),
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "backups": backups
        }


async def main():
    parser = argparse.ArgumentParser(description='Database backup utility')
    parser.add_argument('--environment', default='development', help='Environment to backup')
    parser.add_argument('--compress', action='store_true', help='Compress backup files')
    parser.add_argument('--schema-only', action='store_true', help='Backup schema only (no data)')
    parser.add_argument('--upload-s3', action='store_true', help='Upload backup to S3')
    parser.add_argument('--s3-bucket', help='S3 bucket name for upload')
    parser.add_argument('--cleanup', action='store_true', help='Cleanup old backups')
    parser.add_argument('--retention-days', type=int, default=30, help='Retention period in days')
    parser.add_argument('--verify', action='store_true', help='Verify backup integrity')
    parser.add_argument('--info', action='store_true', help='Show backup information')
    parser.add_argument('--database-url', help='Database URL (overrides settings)')

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('backup.log'),
            logging.StreamHandler()
        ]
    )

    # Get database URL
    database_url = args.database_url or settings.database_url
    if not database_url:
        logger.error("No database URL provided. Set DATABASE_URL or use --database-url")
        sys.exit(1)

    backup_tool = DatabaseBackup(database_url)

    try:
        if args.info:
            info = backup_tool.get_backup_info()
            print(f"Backup Directory: {info['backup_directory']}")
            print(f"Total Backups: {info['total_backups']}")
            print(f"Total Size: {info['total_size_mb']} MB")
            print("\nBackup Files:")
            for backup in info['backups']:
                print(f"  {backup['filename']} - {backup['size_mb']} MB - {backup['created_at']}")
            return

        # Create backup
        backup_path = await backup_tool.create_backup(
            compress=args.compress,
            include_data=not args.schema_only
        )

        # Verify backup if requested
        if args.verify:
            if not await backup_tool.verify_backup(backup_path):
                logger.error("Backup verification failed")
                sys.exit(1)

        # Upload to S3 if requested
        if args.upload_s3:
            if not args.s3_bucket:
                logger.error("S3 bucket name required for upload")
                sys.exit(1)
            await backup_tool.upload_to_s3(backup_path, args.s3_bucket)

        # Cleanup old backups if requested
        if args.cleanup:
            backup_tool.cleanup_old_backups(args.retention_days)

        logger.info("Backup operation completed successfully")

    except Exception as e:
        logger.error(f"Backup operation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())