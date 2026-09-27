import datetime

from league.models import Match, TeamRecord
from league.standings import build_records, filter_as_at, league_table, rank

D = datetime.date(1974, 8, 17)


def match(home, hg, away, ag, date=D):
    return Match(date, home, hg, away, ag)


def summary(rec):
    return (rec.played, rec.won, rec.drawn, rec.lost, rec.goals_for, rec.goals_against, rec.points)


def names(table):
    return [rec.team for _, rec in table]


# --- building records -----------------------------------------------------

def test_home_win_updates_both_teams():
    r = build_records([match("A", 3, "B", 1)])
    assert summary(r["A"]) == (1, 1, 0, 0, 3, 1, 2)
    assert summary(r["B"]) == (1, 0, 0, 1, 1, 3, 0)


def test_away_win_updates_both_teams():
    r = build_records([match("A", 0, "B", 2)])
    assert summary(r["A"]) == (1, 0, 0, 1, 0, 2, 0)
    assert summary(r["B"]) == (1, 1, 0, 0, 2, 0, 2)


def test_draw_updates_both_teams():
    r = build_records([match("A", 1, "B", 1)])
    assert summary(r["A"]) == (1, 0, 1, 0, 1, 1, 1)
    assert summary(r["B"]) == (1, 0, 1, 0, 1, 1, 1)


def test_results_accumulate():
    r = build_records([
        match("A", 2, "B", 0),
        match("C", 1, "A", 1),
        match("B", 0, "A", 3),
    ])
    assert summary(r["A"]) == (3, 2, 1, 0, 6, 1, 5)


def test_no_matches_gives_empty_table():
    assert league_table([]) == []


# --- table invariants -----------------------------------------------------

MATCHES = [
    match("A", 2, "B", 0),
    match("C", 1, "D", 1),
    match("B", 4, "C", 2),
    match("D", 0, "A", 5),
    match("A", 1, "C", 1),
]


def test_played_equals_wins_draws_losses():
    for rec in build_records(MATCHES).values():
        assert rec.played == rec.won + rec.drawn + rec.lost


def test_total_goals_for_equals_total_goals_against():
    recs = build_records(MATCHES).values()
    assert sum(r.goals_for for r in recs) == sum(r.goals_against for r in recs)


def test_total_points_match_results():
    # Each decisive match gives 2 points in total, and each draw 2 as well (1 + 1).
    recs = build_records(MATCHES).values()
    assert sum(r.points for r in recs) == 2 * len(MATCHES)


# --- ranking --------------------------------------------------------------

def test_positions_run_from_one_without_gaps():
    table = league_table(MATCHES)
    assert [pos for pos, _ in table] == [1, 2, 3, 4]


def test_ranked_by_points_then_goal_average_then_goals_then_name():
    table = rank([
        TeamRecord("Zeta", played=1, drawn=1, goals_for=1, goals_against=1),
        TeamRecord("Alpha", played=1, drawn=1, goals_for=1, goals_against=1),
        TeamRecord("Leader", played=1, won=1, goals_for=1, goals_against=0),
        TeamRecord("BetterAvg", played=1, drawn=1, goals_for=2, goals_against=1),
        TeamRecord("MoreGoals", played=1, drawn=1, goals_for=2, goals_against=2),
    ])
    # All but Leader have 1 point. BetterAvg's 2.0 beats 1.0. MoreGoals, Alpha and
    # Zeta all have average 1.0; MoreGoals scored most, then Alpha before Zeta by name.
    assert names(table) == ["Leader", "BetterAvg", "MoreGoals", "Alpha", "Zeta"]


# --- date cutoff ----------------------------------------------------------

def test_as_at_includes_the_cutoff_day_and_excludes_the_next():
    early = match("A", 1, "B", 0, date=datetime.date(1974, 9, 28))
    late = match("B", 1, "A", 0, date=datetime.date(1974, 9, 29))
    assert filter_as_at([early, late], datetime.date(1974, 9, 28)) == [early]


def test_no_cutoff_keeps_everything():
    assert filter_as_at(MATCHES, None) == MATCHES


def test_league_table_applies_the_cutoff():
    ms = [
        match("A", 1, "B", 0, date=datetime.date(1974, 9, 28)),
        match("B", 3, "A", 0, date=datetime.date(1974, 10, 5)),
    ]
    table = league_table(ms, as_at=datetime.date(1974, 9, 28))
    assert names(table) == ["A", "B"]
    assert table[0][1].played == 1


def test_team_with_only_later_matches_is_left_out():
    ms = [
        match("A", 1, "B", 0, date=datetime.date(1974, 9, 28)),
        match("C", 1, "D", 0, date=datetime.date(1974, 10, 5)),
    ]
    assert names(league_table(ms, as_at=datetime.date(1974, 9, 28))) == ["A", "B"]
