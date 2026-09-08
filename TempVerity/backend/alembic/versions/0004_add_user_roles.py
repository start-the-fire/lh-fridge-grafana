"""add administrator and viewer roles"""

from alembic import op
import sqlalchemy as sa


revision = "0004_add_user_roles"
down_revision = "0003_add_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("role", sa.String(24), nullable=False, server_default="admin"))


def downgrade() -> None:
    op.drop_column("users", "role")
