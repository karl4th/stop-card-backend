from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Admin, AuditLog


def add_audit_log(
    session: AsyncSession,
    *,
    admin: Admin,
    action: str,
    entity_type: str,
    entity_id: str,
    changes: dict[str, Any] | None = None,
) -> None:
    session.add(
        AuditLog(
            admin_id=admin.id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            changes=changes,
        )
    )
