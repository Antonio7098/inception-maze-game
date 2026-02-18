"""Remove openrouter_api_key column from users

Revision ID: 001
Revises:
Create Date: 2026-02-18

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("users", "openrouter_api_key")


def downgrade() -> None:
    op.add_column(
        "users", sa.Column("openrouter_api_key", sa.String(255), nullable=True)
    )
