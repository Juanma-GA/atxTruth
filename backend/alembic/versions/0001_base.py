"""Base: users, refresh tokens, audit events, functional settings (with their seed).

Revision ID: 0001_base
Revises:
Create Date: 2026-11-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_base"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SETTINGS = [
    {
        "key": "app.name",
        "category": "general",
        "sort_order": 10,
        "value_type": "string",
        "value": "atxTruth",
        "constraints": {"min_length": 1, "max_length": 60},
        "label": {"en": "Application name", "es": "Nombre de la aplicación", "fr": "Nom de l'application"},
        "description": {
            "en": "Name shown in the top bar and on the sign-in screen.",
            "es": "Nombre que aparece en la barra superior y en la pantalla de acceso.",
            "fr": "Nom affiché dans la barre supérieure et sur l'écran de connexion.",
        },
    },
    {
        "key": "i18n.default_language",
        "category": "general",
        "sort_order": 20,
        "value_type": "enum",
        "value": "en",
        "constraints": {"options": ["en", "es", "fr"]},
        "label": {"en": "Default language", "es": "Idioma por defecto", "fr": "Langue par défaut"},
        "description": {
            "en": "Interface language on the sign-in screen and for accounts without their own choice.",
            "es": "Idioma de la interfaz en la pantalla de acceso y para las cuentas sin idioma elegido.",
            "fr": "Langue de l'interface sur l'écran de connexion et pour les comptes sans langue choisie.",
        },
    },
    {
        "key": "session.duration_hours",
        "category": "security",
        "sort_order": 10,
        "value_type": "integer",
        "value": 12,
        "constraints": {"min": 1, "max": 720, "unit": "hours"},
        "label": {"en": "Session duration", "es": "Duración de la sesión", "fr": "Durée de la session"},
        "description": {
            "en": "How long a sign-in lasts before the user has to sign in again. Applies to new sessions.",
            "es": "Cuánto dura un inicio de sesión antes de tener que volver a entrar. Se aplica a las sesiones nuevas.",
            "fr": "Durée d'une connexion avant de devoir se reconnecter. S'applique aux nouvelles sessions.",
        },
    },
    {
        "key": "auth.login_rate_limit",
        "category": "security",
        "sort_order": 20,
        "value_type": "object",
        "value": {"max_attempts": 5, "window_minutes": 15},
        "constraints": {
            "properties": {
                "max_attempts": {
                    "type": "integer",
                    "min": 1,
                    "max": 100,
                    "label": {"en": "Failed attempts", "es": "Intentos fallidos", "fr": "Tentatives échouées"},
                },
                "window_minutes": {
                    "type": "integer",
                    "min": 1,
                    "max": 1440,
                    "unit": "minutes",
                    "label": {"en": "Lockout window", "es": "Ventana de bloqueo", "fr": "Fenêtre de blocage"},
                },
            }
        },
        "label": {"en": "Sign-in attempt limit", "es": "Límite de intentos de acceso", "fr": "Limite de tentatives"},
        "description": {
            "en": "After this many failed sign-ins for an email within the window, sign-in is blocked until it ends.",
            "es": "Tras estos intentos fallidos para un email dentro de la ventana, el acceso se bloquea hasta que acabe.",
            "fr": "Après ce nombre d'échecs pour un e-mail dans la fenêtre, la connexion est bloquée jusqu'à sa fin.",
        },
    },
    {
        "key": "auth.password_min_length",
        "category": "security",
        "sort_order": 30,
        "value_type": "integer",
        "value": 12,
        "constraints": {"min": 8, "max": 64, "unit": "characters"},
        "label": {
            "en": "Minimum password length",
            "es": "Longitud mínima de la contraseña",
            "fr": "Longueur minimale du mot de passe",
        },
        "description": {
            "en": "Applies when a user sets a new password.",
            "es": "Se aplica cuando un usuario pone una contraseña nueva.",
            "fr": "S'applique lorsqu'un utilisateur définit un nouveau mot de passe.",
        },
    },
    {
        "key": "ui.table_page_size",
        "category": "interface",
        "sort_order": 10,
        "value_type": "integer",
        "value": 25,
        "constraints": {"min": 5, "max": 200, "unit": "rows"},
        "label": {"en": "Table page size", "es": "Tamaño de página de las tablas", "fr": "Taille de page des tableaux"},
        "description": {
            "en": "Rows per page in the application's tables.",
            "es": "Filas por página en las tablas de la aplicación.",
            "fr": "Lignes par page dans les tableaux de l'application.",
        },
    },
    {
        "key": "uploads.max_image_mb",
        "category": "content",
        "sort_order": 10,
        "value_type": "number",
        "value": 5,
        "constraints": {"min": 0.1, "max": 50, "unit": "megabytes"},
        "label": {"en": "Maximum image size", "es": "Tamaño máximo de imagen", "fr": "Taille maximale d'image"},
        "description": {
            "en": "Largest image accepted when uploading (stored in the database).",
            "es": "Imagen más grande que se acepta al subirla (se guarda en la base de datos).",
            "fr": "Image la plus grande acceptée au téléversement (stockée dans la base).",
        },
    },
]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("password_hash", sa.String(200)),
        sa.Column("external_subject", sa.String(255)),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("preferred_language", sa.String(2)),
        sa.Column("theme", sa.String(8), nullable=False, server_default="system"),
        sa.Column("must_change_password", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.CheckConstraint("role IN ('admin', 'editor', 'viewer')", name="role_valid"),
        sa.CheckConstraint("preferred_language IS NULL OR preferred_language IN ('en', 'es', 'fr')", name="language"),
        sa.CheckConstraint("theme IN ('system', 'light', 'dark')", name="theme_valid"),
        sa.CheckConstraint("email = lower(email)", name="email_lowercase"),
        sa.UniqueConstraint("external_subject"),
    )
    op.create_index("uq_users_email", "users", ["email"], unique=True)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("rotated_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("actor_email", sa.String(320)),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("target_type", sa.String(64), nullable=False),
        sa.Column("target_id", sa.String(64)),
        sa.Column("target_label", sa.String(320)),
        sa.Column("before", postgresql.JSONB),
        sa.Column("after", postgresql.JSONB),
        sa.Column("ip", sa.String(64)),
    )
    op.create_index("ix_audit_events_action_label_time", "audit_events", ["action", "target_label", "occurred_at"])
    op.create_index("ix_audit_events_occurred_at", "audit_events", ["occurred_at"])

    settings_table = op.create_table(
        "app_settings",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("value_type", sa.String(16), nullable=False),
        sa.Column("value", postgresql.JSONB, nullable=False),
        sa.Column("default_value", postgresql.JSONB, nullable=False),
        sa.Column("constraints", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("label", postgresql.JSONB, nullable=False),
        sa.Column("description", postgresql.JSONB, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.CheckConstraint(
            "value_type IN ('string', 'integer', 'number', 'boolean', 'enum', 'object')", name="value_type_valid"
        ),
    )
    op.bulk_insert(settings_table, [{**s, "default_value": s["value"]} for s in SETTINGS])


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_table("audit_events")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
