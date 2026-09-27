"""Write a ranked league table as CSV."""

from __future__ import annotations

import csv
import math
from fractions import Fraction
from typing import Iterable, TextIO

from league.models import TeamRecord

HEADER = ["Pos", "Team", "P", "W", "D", "L", "GF", "GA", "GAvg", "Pts"]


def format_goal_average(goals_for: int, goals_against: int) -> str:
    """Goal average to 3 decimal places (half up), or "-" if nothing conceded.

    Rounded from the exact fraction, so no float error and no locale influence.
    Display only: ranking uses the exact value (see rules.goal_average_key).
    """
    if goals_against == 0:
        return "-"
    thousandths = math.floor(Fraction(goals_for, goals_against) * 1000 + Fraction(1, 2))
    whole, frac = divmod(thousandths, 1000)
    return f"{whole}.{frac:03d}"


def write_table(ranked: Iterable[tuple[int, TeamRecord]], stream: TextIO) -> None:
    """Write the header and one row per team, with LF line endings."""
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(HEADER)
    for pos, rec in ranked:
        writer.writerow([
            pos,
            rec.team,
            rec.played,
            rec.won,
            rec.drawn,
            rec.lost,
            rec.goals_for,
            rec.goals_against,
            format_goal_average(rec.goals_for, rec.goals_against),
            rec.points,
        ])
