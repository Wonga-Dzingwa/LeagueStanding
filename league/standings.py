"""Build and rank a league table from match results."""

from __future__ import annotations

import datetime
from typing import Iterable

from league import rules
from league.models import Match, TeamRecord


def filter_as_at(matches: Iterable[Match], as_at: datetime.date | None) -> list[Match]:
    """Keep matches played on or before `as_at` (inclusive); all matches if None."""
    if as_at is None:
        return list(matches)
    return [m for m in matches if m.date <= as_at]


def build_records(matches: Iterable[Match]) -> dict[str, TeamRecord]:
    """Add each result to both teams' records."""
    records: dict[str, TeamRecord] = {}
    for m in matches:
        home = records.setdefault(m.home_team, TeamRecord(m.home_team))
        away = records.setdefault(m.away_team, TeamRecord(m.away_team))
        _add_result(home, scored=m.home_goals, conceded=m.away_goals)
        _add_result(away, scored=m.away_goals, conceded=m.home_goals)
    return records


def rank(records: Iterable[TeamRecord]) -> list[tuple[int, TeamRecord]]:
    """Order records by the 1974/75 rules and number them 1..n.

    Team name is the final tie-break, so positions are never shared.
    """
    ordered = sorted(records, key=rules.ranking_key)
    return list(enumerate(ordered, start=1))


def league_table(
    matches: Iterable[Match], as_at: datetime.date | None = None
) -> list[tuple[int, TeamRecord]]:
    """Filter by date, build records and rank them."""
    return rank(build_records(filter_as_at(matches, as_at)).values())


def _add_result(record: TeamRecord, scored: int, conceded: int) -> None:
    record.played += 1
    record.goals_for += scored
    record.goals_against += conceded
    if scored > conceded:
        record.won += 1
    elif scored == conceded:
        record.drawn += 1
    else:
        record.lost += 1
