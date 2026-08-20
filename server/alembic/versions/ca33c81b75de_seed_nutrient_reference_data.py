"""seed nutrient reference data

Revision ID: ca33c81b75de
Revises: 7455e4b31551
Create Date: 2026-08-21 00:47:24.488359

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'ca33c81b75de'
down_revision: Union[str, None] = '7455e4b31551'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# code, display_name, unit, category — beyond the 4 core macros already
# tracked in food_nutrients. Covers what Open Food Facts and USDA FDC both
# commonly expose; enough for v1 micronutrient display and later RDA gap
# analysis (see docs/architecture.md).
NUTRIENTS = [
    ("FIBTG", "Fiber", "g", "macro"),
    ("SUGAR", "Sugars", "g", "macro"),
    ("FASAT", "Saturated fat", "g", "macro"),
    ("NA", "Sodium", "mg", "mineral"),
    ("CHOLE", "Cholesterol", "mg", "other"),
    ("K", "Potassium", "mg", "mineral"),
    ("CA", "Calcium", "mg", "mineral"),
    ("FE", "Iron", "mg", "mineral"),
    ("VITC", "Vitamin C", "mg", "vitamin"),
    ("VITD", "Vitamin D", "mcg", "vitamin"),
    ("VITA", "Vitamin A", "mcg", "vitamin"),
]

nutrient_reference = sa.table(
    "nutrient_reference",
    sa.column("code", sa.String),
    sa.column("display_name", sa.String),
    sa.column("unit", sa.String),
    sa.column("category", sa.String),
)


def upgrade() -> None:
    op.bulk_insert(
        nutrient_reference,
        [
            {"code": code, "display_name": name, "unit": unit, "category": category}
            for code, name, unit, category in NUTRIENTS
        ],
    )


def downgrade() -> None:
    codes = tuple(code for code, *_ in NUTRIENTS)
    op.execute(
        nutrient_reference.delete().where(nutrient_reference.c.code.in_(codes))
    )
