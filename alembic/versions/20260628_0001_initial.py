"""Initial Stopcard schema and reference data."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260628_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "catalog_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("catalog_type", sa.String(32), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("label", sa.String(500), nullable=False),
        sa.Column("group_code", sa.String(64)),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("requires_text", sa.Boolean(), nullable=False, server_default=sa.false()),
        *timestamps(),
        sa.CheckConstraint(
            "catalog_type IN ('reason', 'circumstance', 'hazard')",
            name="ck_catalog_items_valid_catalog_type",
        ),
        sa.UniqueConstraint("catalog_type", "code", name="uq_catalog_items_catalog_type"),
    )
    op.create_index("ix_catalog_items_catalog_type", "catalog_items", ["catalog_type"])
    op.create_index("ix_catalog_items_is_active", "catalog_items", ["is_active"])

    op.create_table(
        "stopcard_statuses",
        sa.Column("code", sa.String(32), primary_key=True),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_terminal", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *timestamps(),
    )
    op.create_table(
        "admins",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *timestamps(),
        sa.UniqueConstraint("username", name="uq_admins_username"),
    )
    op.create_index("ix_admins_username", "admins", ["username"])

    op.create_table(
        "stopcards",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column(
            "status_code", sa.String(32), sa.ForeignKey("stopcard_statuses.code"), nullable=False
        ),
        sa.Column("author_last_name", sa.String(200), nullable=False),
        sa.Column("author_first_name", sa.String(200), nullable=False),
        sa.Column("author_patronymic", sa.String(200)),
        sa.Column("worker_full_name", sa.String(300), nullable=False),
        sa.Column("worker_department", sa.String(300), nullable=False),
        sa.Column("worker_object", sa.String(300), nullable=False),
        sa.Column("reason_code", sa.String(64), nullable=False),
        sa.Column("circumstance_codes", sa.JSON(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("hazard_codes", sa.JSON(), nullable=False),
        sa.Column("hazard_other_text", sa.Text()),
        sa.Column("corrective", sa.Text(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger()),
        sa.Column("telegram_username", sa.String(100)),
        sa.Column("telegram_auth_date", sa.DateTime(timezone=True)),
        sa.Column("telegram_user_snapshot", sa.JSON()),
        sa.Column("photo_object_key", sa.String(500)),
        sa.Column("photo_content_type", sa.String(100)),
        sa.Column("photo_size", sa.Integer()),
        *timestamps(),
    )
    op.create_index("ix_stopcards_status_code", "stopcards", ["status_code"])
    op.create_index("ix_stopcards_reason_code", "stopcards", ["reason_code"])
    op.create_index("ix_stopcards_telegram_user_id", "stopcards", ["telegram_user_id"])
    op.create_index("ix_stopcards_status_created_at", "stopcards", ["status_code", "created_at"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("admin_id", sa.Uuid()),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(128), nullable=False),
        sa.Column("changes", sa.JSON()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    for column in ("admin_id", "action", "entity_type", "entity_id"):
        op.create_index(f"ix_audit_logs_{column}", "audit_logs", [column])

    catalog = sa.table(
        "catalog_items",
        sa.column("catalog_type", sa.String),
        sa.column("code", sa.String),
        sa.column("label", sa.String),
        sa.column("group_code", sa.String),
        sa.column("display_order", sa.Integer),
        sa.column("requires_text", sa.Boolean),
    )
    rows = [
        ("reason", "accident", "Угроза несчастного случая на производстве", None),
        ("reason", "emergency", "Угроза аварии или инцидента", None),
        ("reason", "traffic", "Угроза дорожно-транспортного происшествия", None),
        ("reason", "fire", "Угроза пожара", None),
        ("reason", "environment", "Угроза загрязнения окружающей среды", None),
        ("circumstance", "w1", "Не проведён инструктаж по безопасному ведению работы", "worker"),
        (
            "circumstance",
            "w2",
            "Отсутствует необходимое обучение, удостоверения или сертификаты",
            "worker",
        ),
        (
            "circumstance",
            "w3",
            "СИЗ отсутствуют или не соответствуют выполняемым работам",
            "worker",
        ),
        ("circumstance", "t1", "Отсутствует необходимое оборудование или инструменты", "tools"),
        ("circumstance", "t2", "Оборудование или инструменты неисправны", "tools"),
        ("circumstance", "t3", "Неправильное использование оборудования или инструментов", "tools"),
        (
            "circumstance",
            "t4",
            "Оборудование или инструменты используются в опасном положении",
            "tools",
        ),
        ("circumstance", "p1", "Неизвестные", "procedures"),
        ("circumstance", "p2", "Не выполняются", "procedures"),
        ("circumstance", "p3", "Непонятные", "procedures"),
        ("circumstance", "e1", "Высокая температура", "environment"),
        ("circumstance", "e2", "Низкая температура", "environment"),
        ("circumstance", "e3", "Шум", "environment"),
        ("circumstance", "e4", "Вибрация", "environment"),
        ("circumstance", "e5", "Химические вещества", "environment"),
        ("circumstance", "e6", "Ионизирующее излучение", "environment"),
        ("circumstance", "e7", "Другие нарушения требований безопасности", "environment"),
        ("hazard", "chemical", "Химическое воздействие", None),
        ("hazard", "mechanical", "Механическое воздействие", None),
        ("hazard", "radiation", "Ионизирующее излучение", None),
        ("hazard", "rotating", "Вращающиеся части машин и механизмов", None),
        ("hazard", "other", "Другой опасный фактор", None),
    ]
    op.bulk_insert(
        catalog,
        [
            {
                "catalog_type": kind,
                "code": code,
                "label": label,
                "group_code": group,
                "display_order": index,
                "requires_text": code == "other",
            }
            for index, (kind, code, label, group) in enumerate(rows, start=1)
        ],
    )
    statuses = sa.table(
        "stopcard_statuses",
        sa.column("code", sa.String),
        sa.column("label", sa.String),
        sa.column("display_order", sa.Integer),
        sa.column("is_terminal", sa.Boolean),
    )
    op.bulk_insert(
        statuses,
        [
            {"code": "created", "label": "Создана", "display_order": 10, "is_terminal": False},
            {
                "code": "in_review",
                "label": "На рассмотрении",
                "display_order": 20,
                "is_terminal": False,
            },
            {"code": "resolved", "label": "Устранено", "display_order": 30, "is_terminal": True},
            {"code": "rejected", "label": "Отклонена", "display_order": 40, "is_terminal": True},
        ],
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("stopcards")
    op.drop_table("admins")
    op.drop_table("stopcard_statuses")
    op.drop_table("catalog_items")
