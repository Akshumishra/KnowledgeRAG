"""seed_llm_providers

Revision ID: 9c2a449db7dd
Revises: fb394d8bcc9f
Create Date: 2026-08-01 20:55:26.506413

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c2a449db7dd'
down_revision: Union[str, Sequence[str], None] = 'fb394d8bcc9f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        INSERT INTO llm_providers (id, name, slug, default_models, is_local, is_active, created_at, updated_at)
        VALUES 
            ('openai', 'OpenAI', 'openai', 'gpt-4.1-mini, gpt-4.1-nano, gpt-5-nano', false, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
            ('gemini', 'Google Gemini', 'gemini', 'gemini-1.5-pro, gemini-1.5-flash', false, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
            ('groq', 'Groq', 'groq', 'llama3-8b-8192, llama3-70b-8192', false, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
            ('openrouter', 'OpenRouter', 'openrouter', 'google/gemini-1.5-pro, openai/gpt-4o', false, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
            ('ollama', 'Ollama (Local)', 'ollama', 'llama3, mistral', true, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT (slug) DO NOTHING;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
