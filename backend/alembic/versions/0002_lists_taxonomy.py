"""Value lists, catalogue taxonomy (edition V0), audit source and the Excel size setting.

Revision ID: 0002_lists_taxonomy
Revises: 0001_base
Create Date: 2026-11-14
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_lists_taxonomy"
down_revision: str | None = "0001_base"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def _common() -> list[sa.Column]:  # type: ignore[type-arg]
    return [
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
    ]


def _edition_fk() -> sa.Column:  # type: ignore[type-arg]
    return sa.Column(
        "edition_id", UUID, sa.ForeignKey("catalogue_editions.id", ondelete="RESTRICT"), nullable=False, index=True
    )


def upgrade() -> None:
    op.add_column("audit_events", sa.Column("source", sa.String(16), nullable=False, server_default="ui"))
    op.add_column("audit_events", sa.Column("source_detail", sa.String(255)))
    op.create_index("ix_audit_events_target", "audit_events", ["target_type", "target_id"])

    op.create_table(
        "value_lists",
        *_common(),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", postgresql.JSONB, nullable=False),
        sa.Column("description", postgresql.JSONB),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.create_index(
        "uq_value_lists_code_active",
        "value_lists",
        ["code"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_table(
        "value_list_items",
        *_common(),
        sa.Column("list_id", UUID, sa.ForeignKey("value_lists.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("label", postgresql.JSONB, nullable=False),
        sa.Column("description", postgresql.JSONB),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    op.create_index(
        "uq_value_list_items_list_code_active",
        "value_list_items",
        ["list_id", "code"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    editions = op.create_table(
        "catalogue_editions",
        *_common(),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", postgresql.JSONB, nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.CheckConstraint("status IN ('active', 'draft', 'archived')", name="status_valid"),
    )
    op.create_index(
        "uq_catalogue_editions_code_active",
        "catalogue_editions",
        ["code"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_table(
        "blocks",
        *_common(),
        _edition_fk(),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", postgresql.JSONB, nullable=False),
        sa.Column("owner", sa.String(200)),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_table(
        "families",
        *_common(),
        _edition_fk(),
        sa.Column("block_id", UUID, sa.ForeignKey("blocks.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", postgresql.JSONB, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="catalogue"),
        sa.Column("source_ref", sa.String(64)),
        sa.CheckConstraint("status IN ('catalogue', 'proposed')", name="status_valid"),
    )
    op.create_table(
        "services",
        *_common(),
        _edition_fk(),
        sa.Column("family_id", UUID, sa.ForeignKey("families.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", postgresql.JSONB, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="catalogue"),
        sa.Column("source_ref", sa.String(64)),
        sa.CheckConstraint("status IN ('catalogue', 'proposed')", name="status_valid"),
    )
    op.create_table(
        "solutions",
        *_common(),
        _edition_fk(),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", postgresql.JSONB, nullable=False),
        sa.Column("solution_types", postgresql.ARRAY(sa.Integer), nullable=False, server_default="{}"),
    )
    op.create_table(
        "adjacent_activities",
        *_common(),
        _edition_fk(),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("activity", postgresql.JSONB, nullable=False),
    )
    for table in ("blocks", "families", "services", "solutions", "adjacent_activities"):
        op.create_index(
            f"uq_{table}_edition_code_active",
            table,
            ["edition_id", "code"],
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        )

    op.bulk_insert(
        editions,
        [
            {
                "id": uuid.UUID("00000000-0000-4000-8000-0000000000a0"),
                "code": "V0",
                "name": {"en": "Catalogue V0", "es": "Catálogo V0", "fr": "Catalogue V0"},
                "status": "active",
            }
        ],
    )

    settings = sa.table(
        "app_settings",
        sa.column("key", sa.String),
        sa.column("category", sa.String),
        sa.column("sort_order", sa.Integer),
        sa.column("value_type", sa.String),
        sa.column("value", postgresql.JSONB),
        sa.column("default_value", postgresql.JSONB),
        sa.column("constraints", postgresql.JSONB),
        sa.column("label", postgresql.JSONB),
        sa.column("description", postgresql.JSONB),
    )
    op.bulk_insert(
        settings,
        [
            {
                "key": "uploads.max_excel_mb",
                "category": "content",
                "sort_order": 20,
                "value_type": "number",
                "value": 10,
                "default_value": 10,
                "constraints": {"min": 0.5, "max": 100, "unit": "megabytes"},
                "label": {
                    "en": "Maximum Excel file size",
                    "es": "Tamaño máximo de fichero Excel",
                    "fr": "Taille maximale du fichier Excel",
                },
                "description": {
                    "en": "Largest .xlsx file accepted when importing lists, catalogue or references.",
                    "es": "Fichero .xlsx más grande que se acepta al importar listas, catálogo o referencias.",
                    "fr": "Fichier .xlsx le plus volumineux accepté à l'import des listes, du catalogue ou des références.",
                },
            }
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM app_settings WHERE key = 'uploads.max_excel_mb'")
    for table in ("adjacent_activities", "solutions", "services", "families", "blocks", "catalogue_editions"):
        op.drop_table(table)
    op.drop_table("value_list_items")
    op.drop_table("value_lists")
    op.drop_index("ix_audit_events_target", table_name="audit_events")
    op.drop_column("audit_events", "source_detail")
    op.drop_column("audit_events", "source")
