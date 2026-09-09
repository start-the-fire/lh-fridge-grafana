"""add stable alarm identity and acknowledgement workflow fields"""

from alembic import op
import sqlalchemy as sa


revision = "0005_alarm_workflow"
down_revision = "0004_add_user_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("alerts", sa.Column("condition_key", sa.String(160), nullable=False, server_default=""))
    op.add_column("alerts", sa.Column("recovery_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("alerts", sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("alerts", sa.Column("acknowledged_by", sa.Integer(), nullable=True))
    op.add_column("alerts", sa.Column("acknowledgement_comment", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("alerts", "acknowledgement_comment")
    op.drop_column("alerts", "acknowledged_by")
    op.drop_column("alerts", "acknowledged_at")
    op.drop_column("alerts", "recovery_started_at")
    op.drop_column("alerts", "condition_key")
