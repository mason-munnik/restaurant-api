"""add restaurants table and fk on reviews

Revision ID: 7409d3949ef4
Revises: b19f8021b383
Create Date: 2026-08-09 10:18:22.024314

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7409d3949ef4"
down_revision: str | Sequence[str] | None = "b19f8021b383"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "restaurants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("cuisine", sa.String(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_restaurants_id"), "restaurants", ["id"], unique=False)

    # SQLite can't ALTER a column's nullability or ADD a foreign key
    # constraint to an existing table in place -- batch mode does the
    # standard copy-new-table-and-swap dance instead.
    with op.batch_alter_table("reviews") as batch_op:
        batch_op.alter_column(
            "restaurant_id", existing_type=sa.INTEGER(), nullable=False
        )
        batch_op.create_index(
            op.f("ix_reviews_restaurant_id"), ["restaurant_id"], unique=False
        )
        batch_op.create_foreign_key(
            "fk_reviews_restaurant_id_restaurants",
            "restaurants",
            ["restaurant_id"],
            ["id"],
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("reviews") as batch_op:
        batch_op.drop_constraint(
            "fk_reviews_restaurant_id_restaurants", type_="foreignkey"
        )
        batch_op.drop_index(op.f("ix_reviews_restaurant_id"))
        batch_op.alter_column(
            "restaurant_id", existing_type=sa.INTEGER(), nullable=True
        )

    op.drop_index(op.f("ix_restaurants_id"), table_name="restaurants")
    op.drop_table("restaurants")
