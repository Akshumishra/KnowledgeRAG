"""fix_missing_display_name_column

Revision ID: fb394d8bcc9f
Revises: a1b2c3d4e5f6
Create Date: 2026-08-01 19:02:28.101396

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb394d8bcc9f'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE organization_api_keys ADD COLUMN IF NOT EXISTS display_name VARCHAR(100);")
    op.execute("ALTER TABLE organization_models ADD COLUMN IF NOT EXISTS api_key_id VARCHAR(36);")


def downgrade() -> None:
    """Downgrade schema."""
    pass
