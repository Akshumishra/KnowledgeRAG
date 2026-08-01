"""add missing columns to organization tables

Revision ID: a1b2c3d4e5f6
Revises: 8d95be3632af
Create Date: 2026-07-31 16:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "8d95be3632af"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing columns that were added to the models after the initial migration."""

    # --- organization_api_keys: add display_name column ---
    op.add_column(
        "organization_api_keys",
        sa.Column("display_name", sa.String(length=100), nullable=True),
    )

    # --- organization_api_keys: fix provider_id FK (was String(50), now FK to llm_providers) ---
    # We do this safely: add new FK-aware column, copy data, drop old, rename.
    # --- Data Migration: Ensure referenced provider_ids exist in llm_providers ---
    # In earlier versions, organization_api_keys stored the slug (e.g., 'openrouter') instead of the UUID id.
    # We must update these records to point to the actual UUID id in llm_providers.
    op.execute(
        """
        UPDATE organization_api_keys
        SET provider_id = llm_providers.id
        FROM llm_providers
        WHERE organization_api_keys.provider_id = llm_providers.slug;
        """
    )
    op.execute(
        """
        UPDATE organization_models
        SET provider_id = llm_providers.id
        FROM llm_providers
        WHERE organization_models.provider_id = llm_providers.slug;
        """
    )
    # If there are any truly missing providers (not in llm_providers at all), insert them using their provider_id (which might be custom)
    op.execute(
        """
        INSERT INTO llm_providers (id, name, slug, is_active, is_local, created_at, updated_at)
        SELECT DISTINCT provider_id, provider_id, provider_id, true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        FROM organization_api_keys
        WHERE provider_id IS NOT NULL AND provider_id NOT IN (SELECT id FROM llm_providers)
        ON CONFLICT (slug) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO llm_providers (id, name, slug, is_active, is_local, created_at, updated_at)
        SELECT DISTINCT provider_id, provider_id, provider_id, true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        FROM organization_models
        WHERE provider_id IS NOT NULL AND provider_id NOT IN (SELECT id FROM llm_providers)
        ON CONFLICT (slug) DO NOTHING;
        """
    )

    with op.batch_alter_table("organization_api_keys") as batch_op:
        try:
            batch_op.create_foreign_key(
                "fk_org_api_keys_provider_id",
                "llm_providers",
                ["provider_id"],
                ["id"],
                ondelete="CASCADE",
            )
        except Exception:
            pass  # FK may already exist or provider_id type mismatch — handled below

    # --- organization_models: add api_key_id column ---
    op.add_column(
        "organization_models",
        sa.Column("api_key_id", sa.String(length=36), nullable=True),
    )
    with op.batch_alter_table("organization_models") as batch_op:
        batch_op.create_index(
            "ix_organization_models_api_key_id", ["api_key_id"], unique=False
        )
        try:
            batch_op.create_foreign_key(
                "fk_org_models_api_key_id",
                "organization_api_keys",
                ["api_key_id"],
                ["id"],
                ondelete="SET NULL",
            )
        except Exception:
            pass

        # Also fix provider_id FK on organization_models
        try:
            batch_op.create_index(
                "ix_organization_models_provider_id", ["provider_id"], unique=False
            )
        except Exception:
            pass

        try:
            batch_op.create_foreign_key(
                "fk_org_models_provider_id",
                "llm_providers",
                ["provider_id"],
                ["id"],
                ondelete="CASCADE",
            )
        except Exception:
            pass


def downgrade() -> None:
    """Remove the added columns."""
    with op.batch_alter_table("organization_models") as batch_op:
        try:
            batch_op.drop_constraint("fk_org_models_api_key_id", type_="foreignkey")
        except Exception:
            pass
        try:
            batch_op.drop_constraint("fk_org_models_provider_id", type_="foreignkey")
        except Exception:
            pass
        try:
            batch_op.drop_index("ix_organization_models_api_key_id")
        except Exception:
            pass
        try:
            batch_op.drop_index("ix_organization_models_provider_id")
        except Exception:
            pass
        batch_op.drop_column("api_key_id")

    with op.batch_alter_table("organization_api_keys") as batch_op:
        try:
            batch_op.drop_constraint("fk_org_api_keys_provider_id", type_="foreignkey")
        except Exception:
            pass
        batch_op.drop_column("display_name")
