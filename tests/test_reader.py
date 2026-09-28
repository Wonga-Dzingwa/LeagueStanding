import datetime
import io

import pytest

from league.models import Match
from league.reader import InputDataError, read_matches, read_matches_bytes

HEADER = "date,home_team,home_goals,away_team,away_goals\n"


def read(text):
    return read_matches(io.StringIO(text, newline=""))


def error_for(text):
    with pytest.raises(InputDataError) as info:
        read(text)
    return info.value


# --- valid input ----------------------------------------------------------

def test_parses_valid_rows():
    matches = read(
        HEADER
        + "1974-08-17,Everton,0,Derby County,0\n"
        + "1974-08-17,Chelsea,0,Carlisle United,2\n"
    )
    assert matches == [
        Match(datetime.date(1974, 8, 17), "Everton", 0, "Derby County", 0),
        Match(datetime.date(1974, 8, 17), "Chelsea", 0, "Carlisle United", 2),
    ]


def test_header_only_gives_no_matches():
    assert read(HEADER) == []


def test_utf8_bom_is_accepted():
    assert len(read("﻿" + HEADER + "1974-08-17,Everton,0,Derby County,0\n")) == 1


def test_windows_line_endings_are_accepted():
    text = HEADER.replace("\n", "\r\n") + "1974-08-17,Everton,0,Derby County,0\r\n"
    assert len(read(text)) == 1


def test_surrounding_spaces_are_trimmed():
    [m] = read(HEADER + "1974-08-17, Everton , 1 , Derby County , 0\n")
    assert (m.home_team, m.home_goals, m.away_team) == ("Everton", 1, "Derby County")


def test_quoted_team_names_with_commas():
    [m] = read(HEADER + '1974-08-17,"Brighton, Hove",1,Everton,0\n')
    assert m.home_team == "Brighton, Hove"


def test_same_pairing_reversed_is_not_a_duplicate():
    assert len(read(
        HEADER
        + "1974-08-17,Everton,0,Derby County,0\n"
        + "1975-01-18,Derby County,0,Everton,1\n"
    )) == 2


# --- bad input: each fails with the right line number ---------------------

GOOD = "1974-08-17,Everton,0,Derby County,0\n"


@pytest.mark.parametrize(
    "bad_row, reason_fragment",
    [
        ("1974-08-17,Everton,0,Derby County\n", "expected 5 columns, got 4"),
        ("1974-08-17,Everton,0,Derby County,0,extra\n", "expected 5 columns, got 6"),
        ("1974-08-17,,0,Derby County,0\n", "home_team is blank"),
        ("1974-08-17,Everton,0,  ,0\n", "away_team is blank"),
        ("1974-08-17,Everton,0,Everton,0\n", "cannot play itself"),
        ("1974-08-17,Everton,x,Derby County,0\n", "home_goals 'x'"),
        ("1974-08-17,Everton,0,Derby County,-1\n", "away_goals '-1'"),
        ("1974-08-17,Everton,1.0,Derby County,0\n", "home_goals '1.0'"),
        ("1974-08-17,Everton,,Derby County,0\n", "home_goals ''"),
        ("17/08/1974,Everton,0,Derby County,0\n", "date '17/08/1974'"),
        ("1974-02-30,Everton,0,Derby County,0\n", "date '1974-02-30'"),
        ("19740817,Everton,0,Derby County,0\n", "date '19740817'"),
        ("\n", "blank line"),
    ],
)
def test_bad_row_reports_its_line_number(bad_row, reason_fragment):
    # Header is line 1, three good rows are lines 2-4, the bad row is line 5.
    good_rows = [
        "1974-08-17,Everton,0,Derby County,0\n",
        "1974-08-17,Chelsea,0,Carlisle United,2\n",
        "1974-08-17,Burnley,1,Wolverhampton Wanderers,2\n",
    ]
    err = error_for(HEADER + "".join(good_rows) + bad_row)
    assert err.line_no == 5
    assert reason_fragment in err.reason
    assert str(err).startswith("line 5: ")


def test_empty_file_is_an_error():
    err = error_for("")
    assert err.line_no == 1
    assert "empty" in err.reason


def test_wrong_header_is_an_error():
    err = error_for("Date,Home,HG,Away,AG\n" + GOOD)
    assert err.line_no == 1
    assert "expected header" in err.reason


def test_duplicate_fixture_names_both_lines():
    err = error_for(HEADER + GOOD + "1974-08-17,Chelsea,0,Carlisle United,2\n" + GOOD)
    assert err.line_no == 4
    assert "already on line 2" in err.reason


def test_malformed_csv_is_an_error():
    err = error_for(HEADER + GOOD + '1974-08-17,"Everton,0,Derby County,0\n')
    assert "malformed CSV" in err.reason


# --- team name spelling ---------------------------------------------------

def test_team_names_differing_only_in_case_are_an_error():
    err = error_for(
        HEADER
        + "1974-08-17,Everton,1,Chelsea,0\n"
        + "1974-08-24,Arsenal,0,everton,1\n"
    )
    assert err.line_no == 3
    assert "'everton' differs only in upper/lower case from 'Everton' (line 2)" in err.reason


def test_case_clash_within_one_row_is_an_error():
    err = error_for(HEADER + "1974-08-17,Everton,1,EVERTON,0\n")
    assert err.line_no == 2
    assert "upper/lower case" in err.reason


def test_same_spelling_everywhere_is_fine():
    assert len(read(
        HEADER
        + "1974-08-17,Everton,1,Chelsea,0\n"
        + "1974-08-24,Arsenal,0,Everton,1\n"
    )) == 2


def test_names_that_differ_by_more_than_case_are_separate_teams():
    # Not treated as a clash: only an upper/lower case difference is flagged.
    ms = read(HEADER + "1974-08-17,Everton,1,Everton Reserves,0\n")
    assert (ms[0].home_team, ms[0].away_team) == ("Everton", "Everton Reserves")


# --- raw bytes / encoding -------------------------------------------------

def many_rows(n):
    return HEADER + "".join(f"1974-08-17,Team{i},1,Other{i},0\n" for i in range(2, n + 1))


def test_bytes_input_parses_like_text():
    assert len(read_matches_bytes(many_rows(10).encode("utf-8"))) == 9


def test_bytes_input_accepts_bom_and_crlf():
    data = b"\xef\xbb\xbf" + (HEADER + GOOD).replace("\n", "\r\n").encode("utf-8")
    assert len(read_matches_bytes(data)) == 1


def test_bytes_input_keeps_non_ascii_names():
    [m] = read_matches_bytes((HEADER + "1974-08-17,München,1,Everton,0\n").encode("utf-8"))
    assert m.home_team == "München"


def test_invalid_byte_deep_in_a_large_file_reports_its_real_line():
    # Well past the 8 KB chunk size where text streams misreport the line.
    lines = many_rows(400).encode("utf-8").split(b"\n")
    lines[299] = lines[299].replace(b"Team300", b"Team\xff300")  # line 300
    with pytest.raises(InputDataError) as info:
        read_matches_bytes(b"\n".join(lines))
    assert info.value.line_no == 300
    assert "0xff" in info.value.reason


def test_latin1_file_reports_the_line_with_the_bad_byte():
    data = (HEADER + "1974-08-17,München,1,Everton,0\n").encode("latin-1")
    with pytest.raises(InputDataError) as info:
        read_matches_bytes(data)
    assert info.value.line_no == 2
    assert "UTF-8" in info.value.reason


def test_first_bad_row_stops_the_read():
    err = error_for(
        HEADER
        + "1974-08-17,Everton,x,Derby County,0\n"
        + "1974-08-17,Chelsea,y,Carlisle United,2\n"
    )
    assert err.line_no == 2
