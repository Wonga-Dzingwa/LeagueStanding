import io
import subprocess
import sys
from pathlib import Path

import pytest

from league import cli
from league.cli import EXIT_BAD_ARGS, EXIT_BAD_DATA, EXIT_INTERNAL, EXIT_OK, main

ROOT = Path(__file__).resolve().parent.parent

RESULTS = (
    "date,home_team,home_goals,away_team,away_goals\n"
    "1974-09-28,Stoke City,1,Derby County,1\n"
    "1974-09-28,Newcastle United,1,Ipswich Town,0\n"
    "1974-10-05,Derby County,2,Newcastle United,0\n"
)
TABLE_ALL = (
    "Pos,Team,P,W,D,L,GF,GA,GAvg,Pts\n"
    "1,Derby County,2,1,1,0,3,1,3.000,3\n"
    "2,Newcastle United,2,1,0,1,1,2,0.500,2\n"
    "3,Stoke City,1,0,1,0,1,1,1.000,1\n"
    "4,Ipswich Town,1,0,0,1,0,1,0.000,0\n"
)


def run(argv, stdin_text=""):
    out, err = io.StringIO(), io.StringIO()
    code = main(argv, stdin=io.BytesIO(stdin_text.encode("utf-8")), stdout=out, stderr=err)
    return code, out.getvalue(), err.getvalue()


@pytest.fixture
def results_file(tmp_path):
    path = tmp_path / "results.csv"
    path.write_text(RESULTS, encoding="utf-8", newline="")
    return path


# --- success --------------------------------------------------------------

def test_stdin_to_stdout():
    assert run([], RESULTS) == (EXIT_OK, TABLE_ALL, "")


def test_dash_means_stdin():
    assert run(["-"], RESULTS) == (EXIT_OK, TABLE_ALL, "")


def test_file_to_stdout(results_file):
    assert run([str(results_file)]) == (EXIT_OK, TABLE_ALL, "")


def test_file_to_output_file_creates_folders(results_file, tmp_path):
    target = tmp_path / "nested" / "output" / "table.csv"
    code, out, err = run([str(results_file), "-o", str(target)])
    assert (code, out, err) == (EXIT_OK, "", "")
    assert target.read_bytes() == TABLE_ALL.encode("utf-8")  # exact bytes: LF only


def test_as_at_filters_matches(results_file):
    code, out, _ = run([str(results_file), "--as-at", "1974-09-28"])
    assert code == EXIT_OK
    assert out.splitlines()[1:] == [
        "1,Newcastle United,1,1,0,0,1,0,-,2",
        "2,Derby County,1,0,1,0,1,1,1.000,1",
        "3,Stoke City,1,0,1,0,1,1,1.000,1",
        "4,Ipswich Town,1,0,0,1,0,1,0.000,0",
    ]


def test_as_at_before_any_match_warns_but_exits_0(results_file):
    code, out, err = run([str(results_file), "--as-at", "1974-01-01"])
    assert code == EXIT_OK
    assert out == "Pos,Team,P,W,D,L,GF,GA,GAvg,Pts\n"
    assert err == "league: warning: no matches on or before 1974-01-01; the table is empty\n"


def test_as_at_that_keeps_matches_gives_no_warning(results_file):
    assert run([str(results_file), "--as-at", "1974-09-28"])[2] == ""


def test_no_as_at_on_header_only_input_gives_no_warning():
    code, out, err = run([], "date,home_team,home_goals,away_team,away_goals\n")
    assert (code, err) == (EXIT_OK, "")
    assert out == "Pos,Team,P,W,D,L,GF,GA,GAvg,Pts\n"


def test_help_goes_to_stdout_and_exits_zero():
    code, out, err = run(["--help"])
    assert code == EXIT_OK
    assert "--as-at" in out and err == ""


# --- bad data: exit 1 -----------------------------------------------------

def test_bad_row_exits_1_with_line_number_on_stderr(results_file):
    results_file.write_text(RESULTS + "1974-10-05,Everton,x,Chelsea,1\n", encoding="utf-8", newline="")
    code, out, err = run([str(results_file)])
    assert code == EXIT_BAD_DATA
    assert out == ""
    assert f"{results_file}: line 5: home_goals 'x'" in err


def test_bad_stdin_names_stdin():
    code, out, err = run([], "wrong,header\n")
    assert (code, out) == (EXIT_BAD_DATA, "")
    assert "<stdin>: line 1:" in err


def test_bad_data_never_writes_output_file(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("date,home_team,home_goals,away_team,away_goals\n1974,A,1,B,0\n", encoding="utf-8")
    target = tmp_path / "table.csv"
    code, _, _ = run([str(bad), "-o", str(target)])
    assert code == EXIT_BAD_DATA
    assert not target.exists()


# --- bad arguments: exit 2 ------------------------------------------------

@pytest.mark.parametrize("value", ["28/09/1974", "1974-02-30", "19740928", "soon"])
def test_bad_as_at_exits_2(value):
    code, out, err = run(["--as-at", value], RESULTS)
    assert (code, out) == (EXIT_BAD_ARGS, "")
    assert "--as-at" in err


def test_unknown_option_exits_2():
    code, out, err = run(["--week", "10"], RESULTS)
    assert (code, out) == (EXIT_BAD_ARGS, "")
    assert "unrecognized arguments" in err


def test_missing_input_file_exits_2(tmp_path):
    code, out, err = run([str(tmp_path / "nope.csv")])
    assert (code, out) == (EXIT_BAD_ARGS, "")
    assert "cannot read input file" in err


def test_input_that_is_a_folder_exits_2(tmp_path):
    code, out, err = run([str(tmp_path)])
    assert (code, out) == (EXIT_BAD_ARGS, "")
    assert "cannot read input file" in err


# --- no input from a terminal: exit 2 -------------------------------------

class TerminalStdin(io.BytesIO):
    def isatty(self):
        return True


def run_with_terminal(argv):
    out, err = io.StringIO(), io.StringIO()
    code = main(argv, stdin=TerminalStdin(RESULTS.encode("utf-8")), stdout=out, stderr=err)
    return code, out.getvalue(), err.getvalue()


def test_no_input_on_a_terminal_prints_usage_and_exits_2():
    code, out, err = run_with_terminal([])
    assert (code, out) == (EXIT_BAD_ARGS, "")
    assert err.startswith("usage: league")
    assert "no input" in err


def test_no_input_on_a_terminal_with_other_options_still_exits_2():
    assert run_with_terminal(["--as-at", "1974-09-28"])[0] == EXIT_BAD_ARGS


def test_explicit_dash_still_reads_a_terminal():
    assert run_with_terminal(["-"]) == (EXIT_OK, TABLE_ALL, "")


def test_file_input_ignores_a_terminal_stdin(results_file):
    assert run_with_terminal([str(results_file)]) == (EXIT_OK, TABLE_ALL, "")


# --- unexpected errors: exit 3 --------------------------------------------

def test_unexpected_error_exits_3_with_one_line_message(monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("something broke")

    monkeypatch.setattr(cli, "league_table", broken)
    code, out, err = run([], RESULTS)
    assert (code, out) == (EXIT_INTERNAL, "")
    assert err == "league: internal error: RuntimeError: something broke\n"


def test_unexpected_error_never_writes_output_file(monkeypatch, results_file, tmp_path):
    monkeypatch.setattr(cli, "write_table", lambda *a: 1 / 0)
    target = tmp_path / "table.csv"
    code, _, err = run([str(results_file), "-o", str(target)])
    assert code == EXIT_INTERNAL
    assert "ZeroDivisionError" in err and err.count("\n") == 1
    assert not target.exists()


# --- real process: `python -m league` -------------------------------------

def run_module(*args, stdin_bytes=b""):
    return subprocess.run(
        [sys.executable, "-m", "league", *args],
        input=stdin_bytes,
        capture_output=True,
        cwd=ROOT,
    )


def test_module_writes_lf_only_csv_to_stdout():
    proc = run_module(stdin_bytes=RESULTS.encode("utf-8"))
    assert proc.returncode == EXIT_OK
    assert proc.stdout == TABLE_ALL.encode("utf-8")  # no "\r\n", even on Windows
    assert proc.stderr == b""


def test_module_exit_codes():
    assert run_module(stdin_bytes=b"bad\n").returncode == EXIT_BAD_DATA
    assert run_module("--as-at", "nope").returncode == EXIT_BAD_ARGS
