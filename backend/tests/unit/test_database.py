"""Unit tests for SQLAlchemy foundation models, UUIDs, UTC timestamps, and Alembic."""

from __future__ import annotations

import uuid
from datetime import UTC
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select

from app.core.config import Settings
from app.database.connection import create_db_engine, create_session_factory
from app.models.audit_log import AuditLog

BACKEND_DIR = Path(__file__).resolve().parents[2]


async def test_alembic_upgrade_and_audit_log_persistence(
    tmp_path: Path,
) -> None:
    db_file = tmp_path / "migration_test.db"
    settings = Settings(
        app_env="testing",
        app_secret_key="test-secret-key-for-jobmate-unit-suite-123456",
        database_url=f"sqlite+aiosqlite:///{db_file}",
    )

    alembic_cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(BACKEND_DIR / "app/database/migrations"))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.sync_database_url)
    command.upgrade(alembic_cfg, "head")

    engine = create_db_engine(settings)
    session_factory = create_session_factory(engine)
    try:
        async with engine.connect() as conn:
            tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
        assert "audit_logs" in tables
        assert "alembic_version" in tables

        user_uuid = uuid.uuid4()
        async with session_factory() as session:
            entry = AuditLog(
                user_id=user_uuid,
                event_type="system.foundation_check",
                resource_type="health",
                resource_id="v1",
                request_id="req-db-1",
                details={"ok": True},
            )
            session.add(entry)
            await session.commit()
            await session.refresh(entry)
            entry_id = entry.id

        async with session_factory() as session:
            loaded = await session.scalar(select(AuditLog).where(AuditLog.id == entry_id))
            assert loaded is not None
            assert loaded.user_id == user_uuid
            assert loaded.event_type == "system.foundation_check"
            assert loaded.details == {"ok": True}
            assert loaded.created_at.tzinfo is not None
            assert loaded.created_at.utcoffset() == UTC.utcoffset(loaded.created_at)
    finally:
        await engine.dispose()

