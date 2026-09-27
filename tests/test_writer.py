import io

import pytest

from league.models import TeamRecord
from league.writer import format_goal_average, write_table


# --- goal average display -------------------------------------------------

@pytest.mark.parametrize(
    "gf, ga, expected",
    [
        (67, 49, "1.367"),   # Derby 1974/75
        (2, 3, "0.667"),     # rounds up
        (1, 3, "0.333"),     # rounds down
        (3, 1, "3.000"),     # whole number keeps 3 places
        (0, 5, "0.000"),
        (1, 8, "0.125"),     # exact, no rounding needed
        (1, 2000, "0.001"),  # exactly half a thousandth rounds up
        (1, 2001, "0.000"),  # just under half rounds down
        (100, 1, "100.000"),
    ],
)
def test_goal_average_to_three_decimals(gf, ga, expected):
    assert format_goal_average(gf, ga) == expected


def test_goal_average_is_dash_when_nothing_conceded():
    assert format_goal_average(5, 0) == "-"
    assert format_goal_average(0, 0) == "-"


# --- table output ---------------------------------------------------------

def rendered(ranked):
    out = io.StringIO(newline="")
    write_table(ranked, out)
    return out.getvalue()


def test_header_and_row_layout():
    text = rendered([
        (1, TeamRecord("Ipswich Town", 10, 8, 0, 2, 18, 6)),
        (2, TeamRecord("Manchester City", 10, 6, 2, 2, 14, 11)),
    ])
    assert text == (
        "Pos,Team,P,W,D,L,GF,GA,GAvg,Pts\n"
        "1,Ipswich Town,10,8,0,2,18,6,3.000,16\n"
        "2,Manchester City,10,6,2,2,14,11,1.273,14\n"
    )


def test_line_endings_are_lf_only():
    text = rendered([(1, TeamRecord("A", 1, 1, 0, 0, 1, 0))])
    assert "\r" not in text


def test_nothing_conceded_shows_dash():
    text = rendered([(1, TeamRecord("A", 1, 1, 0, 0, 2, 0))])
    assert text.splitlines()[1] == "1,A,1,1,0,0,2,0,-,2"


def test_team_name_with_comma_is_quoted():
    text = rendered([(1, TeamRecord("Brighton, Hove", 1, 0, 1, 0, 1, 1))])
    assert text.splitlines()[1] == '1,"Brighton, Hove",1,0,1,0,1,1,1.000,1'


def test_empty_table_is_just_the_header():
    assert rendered([]) == "Pos,Team,P,W,D,L,GF,GA,GAvg,Pts\n"
