import io
import subprocess
import sys
from pathlib import Path

import pytest

from league.cli import EXIT_BAD_ARGS, EXIT_BAD_DATA, EXIT_OK, main

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
    code = main(argv, stdin=io.StringIO(stdin_text, newline=""), stdout=out, stderr=err)
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
