"""seed rda targets

Revision ID: 925708b395a7
Revises: ca33c81b75de
Create Date: 2026-08-21 18:47:06.037063

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '925708b395a7'
down_revision: Union[str, None] = 'ca33c81b75de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Adult (19+) dietary reference intakes, single age bracket — good enough
# for a personal-use app, not a clinical source. Only nutrients with a
# genuine minimum-intake RDA are seeded here; SUGAR/FASAT/NA/CHOLE are
# upper-limit nutrients (not "deficiency" nutrients) and are deliberately
# left unseeded, since compute_nutrient_gaps() only flags shortfalls below
# a target, which wouldn't make sense for an upper limit.
RDA_ROWS = [
    # nutrient_code, sex, rda_amount, unit
    ("FIBTG", "any", 28.0, "g"),
    ("CA", "any", 1000.0, "mg"),
    ("FE", "male", 8.0, "mg"),
    ("FE", "female", 18.0, "mg"),
    ("VITC", "male", 90.0, "mg"),
    ("VITC", "female", 75.0, "mg"),
    ("VITD", "any", 15.0, "mcg"),
    ("VITA", "male", 900.0, "mcg"),
    ("VITA", "female", 700.0, "mcg"),
    ("K", "male", 3400.0, "mg"),
    ("K", "female", 2600.0, "mg"),
]

rda_targets = sa.table(
    "rda_targets",
    sa.column("id", sa.Integer),
    sa.column("nutrient_code", sa.String),
    sa.column("sex", sa.String),
    sa.column("age_min", sa.Integer),
    sa.column("age_max", sa.Integer),
    sa.column("rda_amount", sa.Float),
    sa.column("unit", sa.String),
)


def upgrade() -> None:
    op.bulk_insert(
        rda_targets,
        [
            {
                "nutrient_code": code,
                "sex": sex,
                "age_min": 19,
                "age_max": 120,
                "rda_amount": amount,
                "unit": unit,
            }
            for code, sex, amount, unit in RDA_ROWS
        ],
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM rda_targets WHERE age_min = 19 AND age_max = 120"))
