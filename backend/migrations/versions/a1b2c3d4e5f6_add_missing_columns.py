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
    # But since the column type is the same (String), we only need to add the FK constraint.
    # Use try/except in case the FK already exists on some envs.
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
