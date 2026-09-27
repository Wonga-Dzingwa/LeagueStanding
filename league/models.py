"""Data types for match results and a team's running record."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from fractions import Fraction

from league import rules


@dataclass(frozen=True)
class Match:
    date: datetime.date
    home_team: str
    home_goals: int
    away_team: str
    away_goals: int


@dataclass
class TeamRecord:
    team: str
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0

    @property
    def points(self) -> int:
        return rules.points_for(self.won, self.drawn, self.lost)

    @property
    def goal_average(self) -> tuple[bool, Fraction]:
        """Exact goal average as a comparable (is_infinite, value) key; see rules."""
        return rules.goal_average_key(self.goals_for, self.goals_against)
