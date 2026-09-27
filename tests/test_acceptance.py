"""Acceptance tests on the real 1974/75 First Division data.

Known facts checked against the published 1974/75 final table (Wikipedia):
Derby champions on 53; Liverpool above Ipswich on goal average (both 51);
Luton above Chelsea on goal average (both 33); Luton, Chelsea, Carlisle relegated.
"""

import csv
import io
from pathlib import Path

import pytest

from league.cli import EXIT_OK, main
from league.reader import read_matches

DATA = Path(__file__).resolve().parent.parent / "data"
FULL = DATA / "results_1974_75_full.csv"
WEEK10 = DATA / "results_1974_75_week10.csv"
GOLDEN = DATA / "output" / "standings_1974_75_week10.csv"

NINE_GAMES = {
    "Arsenal", "Leeds United", "Leicester City",
    "Middlesbrough", "Newcastle United", "Tottenham Hotspur",
}


def run_cli(*args):
    out, err = io.StringIO(), io.StringIO()
    code = main(list(args), stdout=out, stderr=err)
    assert (code, err.getvalue()) == (EXIT_OK, "")
    return out.getvalue()


def rows(table_csv):
    return list(csv.DictReader(io.StringIO(table_csv)))


def by_team(table_rows):
    return {r["Team"]: r for r in table_rows}


def count_matches(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return len(read_matches(f))


# --- input data -----------------------------------------------------------

def test_data_files_have_expected_match_counts():
    assert count_matches(FULL) == 462   # 22 clubs x 42 games / 2
    assert count_matches(WEEK10) == 107


# --- full season: matches the published final table -----------------------

@pytest.fixture(scope="module")
def season():
    return rows(run_cli(str(FULL)))


def test_full_season_every_club_played_42(season):
    assert len(season) == 22
    assert {r["P"] for r in season} == {"42"}


def test_derby_are_champions_on_53(season):
    assert (season[0]["Team"], season[0]["Pts"]) == ("Derby County", "53")


def test_liverpool_above_ipswich_on_goal_average(season):
    # Level on 51; Ipswich scored more (66 v 60) but Liverpool's 60/39 beats 66/44.
    assert [(r["Team"], r["Pts"], r["GAvg"]) for r in season[1:3]] == [
        ("Liverpool", "51", "1.538"),
        ("Ipswich Town", "51", "1.500"),
    ]


def test_relegated_clubs_in_order(season):
    # Luton and Chelsea both on 33; Luton's goal average is better.
    assert [(r["Team"], r["Pts"]) for r in season[-3:]] == [
        ("Luton Town", "33"),
        ("Chelsea", "33"),
        ("Carlisle United", "29"),
    ]


# --- gameweek 10 ----------------------------------------------------------

@pytest.fixture(scope="module")
def week10_csv():
    return run_cli(str(WEEK10))


def test_week10_has_all_22_clubs(week10_csv):
    assert len(rows(week10_csv)) == 22


def test_week10_six_clubs_have_played_nine(week10_csv):
    table = rows(week10_csv)
    assert {r["Team"] for r in table if r["P"] == "9"} == NINE_GAMES
    assert {r["P"] for r in table if r["Team"] not in NINE_GAMES} == {"10"}
    assert sum(int(r["P"]) for r in table) == 2 * 107


def test_week10_leader_is_ipswich_on_16(week10_csv):
    top = rows(week10_csv)[0]
    assert (top["Team"], top["P"], top["Pts"], top["GAvg"]) == ("Ipswich Town", "10", "16", "3.000")


def test_week10_level_on_points_ordered_by_goal_average(week10_csv):
    t = by_team(rows(week10_csv))
    # Liverpool, Everton, Sheffield United all on 13.
    assert [t[n]["Pos"] for n in ("Liverpool", "Everton", "Sheffield United")] == ["3", "4", "5"]


def test_full_season_cut_at_28_sep_equals_week10_file(week10_csv):
    assert run_cli(str(FULL), "--as-at", "1974-09-28") == week10_csv


def test_committed_output_matches_fresh_run(week10_csv):
    # If this fails, regenerate with:
    #   python -m league data/results_1974_75_week10.csv -o data/output/standings_1974_75_week10.csv
    assert GOLDEN.read_bytes() == week10_csv.encode("utf-8")
