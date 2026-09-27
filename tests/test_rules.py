import datetime
from fractions import Fraction

import pytest

from league import rules
from league.models import Match, TeamRecord


def record(team, won=0, drawn=0, lost=0, gf=0, ga=0):
    return TeamRecord(
        team=team,
        played=won + drawn + lost,
        won=won,
        drawn=drawn,
        lost=lost,
        goals_for=gf,
        goals_against=ga,
    )


def ranked(*records):
    return [r.team for r in sorted(records, key=rules.ranking_key)]


# --- points ---------------------------------------------------------------

def test_two_points_for_a_win_one_for_a_draw_none_for_a_loss():
    assert rules.points_for(won=1, drawn=0, lost=0) == 2
    assert rules.points_for(won=0, drawn=1, lost=0) == 1
    assert rules.points_for(won=0, drawn=0, lost=1) == 0


def test_team_record_points():
    assert record("A", won=8, drawn=3, lost=2).points == 19


# --- goal average ---------------------------------------------------------

def test_goal_average_is_exact_fraction():
    assert rules.goal_average_key(3, 2) == (False, Fraction(3, 2))


def test_higher_ratio_ranks_higher():
    assert rules.goal_average_key(3, 1) > rules.goal_average_key(2, 1)


def test_no_goals_conceded_beats_any_real_ratio():
    assert rules.goal_average_key(1, 0) > rules.goal_average_key(50, 1)


def test_no_goals_either_way_counts_as_one():
    assert rules.goal_average_key(0, 0) == rules.goal_average_key(7, 7)


def test_goal_average_uses_exact_equality_not_floats():
    # 2/6 and 1/3 are equal exactly; floats could make them differ.
    assert rules.goal_average_key(2, 6) == rules.goal_average_key(1, 3)
    # Ratios that are close but not equal must still be ordered correctly.
    assert rules.goal_average_key(333333, 1000000) < rules.goal_average_key(1, 3)


# --- ranking order --------------------------------------------------------

def test_points_decide_first():
    # B has a far better goal average but fewer points.
    a = record("A", won=2, gf=2, ga=2)
    b = record("B", won=1, drawn=1, gf=10, ga=1)
    assert ranked(b, a) == ["A", "B"]


def test_goal_average_breaks_level_points():
    # Equal points; A has more goals scored but B has the better goal average.
    a = record("A", won=2, gf=10, ga=5)  # 2.0
    b = record("B", won=2, gf=6, ga=2)   # 3.0
    assert ranked(a, b) == ["B", "A"]


def test_goal_average_not_goal_difference():
    # A: difference +6, average 1.6.  B: difference +4, average 3.0.
    a = record("A", won=2, gf=16, ga=10)
    b = record("B", won=2, gf=6, ga=2)
    assert ranked(a, b) == ["B", "A"]


def test_goals_scored_breaks_equal_goal_average():
    # 2/6 == 1/3 exactly, so goals scored decides.
    a = record("A", won=1, gf=1, ga=3)
    b = record("B", won=1, gf=2, ga=6)
    assert ranked(a, b) == ["B", "A"]


def test_two_unbeaten_defences_fall_through_to_goals_scored():
    a = record("A", won=1, gf=1, ga=0)
    b = record("B", won=1, gf=3, ga=0)
    assert ranked(a, b) == ["B", "A"]


def test_team_name_is_final_tie_break():
    a = record("Arsenal", drawn=1, gf=1, ga=1)
    z = record("Wolves", drawn=1, gf=1, ga=1)
    assert ranked(z, a) == ["Arsenal", "Wolves"]


# --- models ---------------------------------------------------------------

def test_match_is_immutable():
    m = Match(datetime.date(1974, 8, 17), "Everton", 0, "Derby County", 0)
    with pytest.raises(AttributeError):
        m.home_goals = 1
