"""Strict CSV reader for match results.

Any bad row stops the read with its line number; nothing is skipped.
Expected header: date,home_team,home_goals,away_team,away_goals
"""

from __future__ import annotations

import csv
import datetime
import re
from typing import Iterable

from league.models import Match

HEADER = ["date", "home_team", "home_goals", "away_team", "away_goals"]

_GOALS = re.compile(r"[0-9]+")
_ISO_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


class InputDataError(Exception):
    """A problem with the input data, tied to a line in the file."""

    def __init__(self, line_no: int, reason: str) -> None:
        super().__init__(f"line {line_no}: {reason}")
        self.line_no = line_no
        self.reason = reason


def read_matches(stream: Iterable[str]) -> list[Match]:
    """Parse match results from a text stream opened with newline=""."""
    reader = csv.reader(stream, strict=True)  # strict: unbalanced quotes are an error
    try:
        return _parse(reader)
    except csv.Error as exc:
        raise InputDataError(reader.line_num, f"malformed CSV: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise InputDataError(reader.line_num + 1, "file is not valid UTF-8 text") from exc


def _parse(reader) -> list[Match]:
    header = next(reader, None)
    if header is None:
        raise InputDataError(1, "file is empty; expected a header row: " + ",".join(HEADER))
    if header:
        header[0] = header[0].removeprefix("﻿")  # BOM when reading stdin
    if [h.strip() for h in header] != HEADER:
        raise InputDataError(
            reader.line_num,
            f"expected header {','.join(HEADER)!r}, got {','.join(header)!r}",
        )

    matches: list[Match] = []
    seen: dict[tuple[str, str], int] = {}
    for row in reader:
        line_no = reader.line_num
        match = _parse_row(row, line_no)
        fixture = (match.home_team, match.away_team)
        if fixture in seen:
            raise InputDataError(
                line_no,
                f"duplicate fixture {match.home_team} v {match.away_team} "
                f"(already on line {seen[fixture]})",
            )
        seen[fixture] = line_no
        matches.append(match)
    return matches


def _parse_row(row: list[str], line_no: int) -> Match:
    if not row:
        raise InputDataError(line_no, "blank line")
    if len(row) != len(HEADER):
        raise InputDataError(line_no, f"expected {len(HEADER)} columns, got {len(row)}")

    date_text, home_team, home_goals, away_team, away_goals = (f.strip() for f in row)
    if not home_team:
        raise InputDataError(line_no, "home_team is blank")
    if not away_team:
        raise InputDataError(line_no, "away_team is blank")
    if home_team == away_team:
        raise InputDataError(line_no, f"{home_team} cannot play itself")

    return Match(
        date=_parse_date(date_text, line_no),
        home_team=home_team,
        home_goals=_parse_goals("home_goals", home_goals, line_no),
        away_team=away_team,
        away_goals=_parse_goals("away_goals", away_goals, line_no),
    )


def _parse_date(text: str, line_no: int) -> datetime.date:
    if _ISO_DATE.fullmatch(text):
        try:
            return datetime.date.fromisoformat(text)
        except ValueError:
            pass
    raise InputDataError(line_no, f"date {text!r} is not a valid YYYY-MM-DD date")


def _parse_goals(column: str, text: str, line_no: int) -> int:
    if not _GOALS.fullmatch(text):
        raise InputDataError(line_no, f"{column} {text!r} is not a whole number of goals (0 or more)")
    return int(text)
