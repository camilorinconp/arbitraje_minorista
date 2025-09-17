#!/usr/bin/env python3
"""
Migration runner script for database schema changes.
Usage: python migrate.py [--dry-run] [--migration=001]
"""

import asyncio
import asyncpg
import os
import sys
import argparse
from pathlib import Path
from typing import List, Optional
import logging

# Add backend to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from core.config import settings

logger = logging.getLogger(__name__)


class MigrationRunner:
    """
    Simple migration runner for PostgreSQL.
    """

    def __init__(self, database_url: str):
        # Convert SQLAlchemy URL to asyncpg format
        if database_url.startswith("postgresql+asyncpg://"):
            self.database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        else:
            self.database_url = database_url
        self.migrations_dir = Path(__file__).parent

    async def create_migrations_table(self, conn: asyncpg.Connection):
        """Create migrations tracking table if it doesn't exist."""
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                id SERIAL PRIMARY KEY,
                migration_name VARCHAR(255) UNIQUE NOT NULL,
                applied_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
            );
        """)

    async def get_applied_migrations(self, conn: asyncpg.Connection) -> List[str]:
        """Get list of already applied migrations."""
        rows = await conn.fetch("SELECT migration_name FROM migrations ORDER BY migration_name")
        return [row['migration_name'] for row in rows]

    async def get_pending_migrations(self, conn: asyncpg.Connection) -> List[Path]:
        """Get list of pending migration files."""
        applied = await self.get_applied_migrations(conn)

        migration_files = []
        for file_path in sorted(self.migrations_dir.glob("*.sql")):
            migration_name = file_path.stem
            if migration_name not in applied:
                migration_files.append(file_path)

        return migration_files

    async def apply_migration(self, conn: asyncpg.Connection, migration_file: Path, dry_run: bool = False):
        """Apply a single migration file."""
        migration_name = migration_file.stem

        logger.info(f"Applying migration: {migration_name}")

        # Read migration file
        sql_content = migration_file.read_text(encoding='utf-8')

        if dry_run:
            print(f"[DRY RUN] Would execute migration: {migration_name}")
            print(f"SQL Content:\n{sql_content}\n")
            return

        try:
            async with conn.transaction():
                # Execute migration SQL
                await conn.execute(sql_content)

                # Record migration as applied
                await conn.execute(
                    "INSERT INTO migrations (migration_name) VALUES ($1)",
                    migration_name
                )

            logger.info(f"Successfully applied migration: {migration_name}")

        except Exception as e:
            logger.error(f"Failed to apply migration {migration_name}: {e}")
            raise

    async def run_migrations(self, dry_run: bool = False, specific_migration: Optional[str] = None):
        """Run all pending migrations or a specific one."""
        conn = await asyncpg.connect(self.database_url)

        try:
            # Create migrations table
            await self.create_migrations_table(conn)

            if specific_migration:
                # Run specific migration
                migration_file = self.migrations_dir / f"{specific_migration}.sql"
                if not migration_file.exists():
                    raise FileNotFoundError(f"Migration file not found: {migration_file}")

                applied = await self.get_applied_migrations(conn)
                if specific_migration in applied:
                    logger.warning(f"Migration {specific_migration} already applied")
                    return

                await self.apply_migration(conn, migration_file, dry_run)
            else:
                # Run all pending migrations
                pending = await self.get_pending_migrations(conn)

                if not pending:
                    logger.info("No pending migrations found")
                    return

                logger.info(f"Found {len(pending)} pending migrations")

                for migration_file in pending:
                    await self.apply_migration(conn, migration_file, dry_run)

                if not dry_run:
                    logger.info(f"Successfully applied {len(pending)} migrations")

        finally:
            await conn.close()

    async def show_status(self):
        """Show migration status."""
        conn = await asyncpg.connect(self.database_url)

        try:
            await self.create_migrations_table(conn)

            applied = await self.get_applied_migrations(conn)
            pending = await self.get_pending_migrations(conn)

            print(f"Applied migrations ({len(applied)}):")
            for migration in applied:
                print(f"  ✅ {migration}")

            print(f"\nPending migrations ({len(pending)}):")
            for migration_file in pending:
                print(f"  ⏳ {migration_file.stem}")

            if not pending:
                print("  (none)")

        finally:
            await conn.close()


async def main():
    parser = argparse.ArgumentParser(description='Database migration runner')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be executed without running')
    parser.add_argument('--migration', help='Run specific migration (e.g., 001_create_auth_tables)')
    parser.add_argument('--status', action='store_true', help='Show migration status')
    parser.add_argument('--database-url', help='Database URL (overrides settings)')

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

    runner = MigrationRunner(database_url)

    try:
        if args.status:
            await runner.show_status()
        else:
            await runner.run_migrations(
                dry_run=args.dry_run,
                specific_migration=args.migration
            )
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())