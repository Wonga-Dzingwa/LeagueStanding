"""Points and ranking rules of the English First Division, 1974/75.

All season-specific rules live here:
- 2 points for a win, 1 for a draw, 0 for a loss (3 for a win only arrived in 1981/82).
- Teams level on points are separated by goal average (goals for / goals against),
  then goals scored. Goal difference replaced goal average only in 1976/77.
- Final fallback is team name A-Z so the order is deterministic (our choice).
"""

from __future__ import annotations

from fractions import Fraction
from typing import Protocol

POINTS_WIN = 2
POINTS_DRAW = 1
POINTS_LOSS = 0


class Rankable(Protocol):
    team: str
    goals_for: int
    goals_against: int

    @property
    def points(self) -> int: ...


def points_for(won: int, drawn: int, lost: int) -> int:
    return won * POINTS_WIN + drawn * POINTS_DRAW + lost * POINTS_LOSS


def goal_average_key(goals_for: int, goals_against: int) -> tuple[bool, Fraction]:
    """Exact, comparable goal average: (is_infinite, value).

    - Conceded goals: the exact ratio goals_for / goals_against.
    - Scored but conceded none: infinite, above any real ratio.
    - Neither scored nor conceded: treated as 1 (neutral).
    """
    if goals_against > 0:
        return (False, Fraction(goals_for, goals_against))
    if goals_for > 0:
        return (True, Fraction(0))
    return (False, Fraction(1))


def ranking_key(record: Rankable) -> tuple:
    """Sort key for `sorted()` (ascending) that puts the league leader first."""
    is_infinite, ratio = goal_average_key(record.goals_for, record.goals_against)
    return (
        -record.points,
        -int(is_infinite),
        -ratio,
        -record.goals_for,
        record.team,
    )
