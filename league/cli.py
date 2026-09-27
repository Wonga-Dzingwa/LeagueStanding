"""Command-line entry point.

Exit codes: 0 ok, 1 bad input data, 2 bad arguments (including an unreadable input file).
Errors go to stderr; stdout carries only the CSV table.
"""

from __future__ import annotations

import argparse
import datetime
import io
import sys
from pathlib import Path
from typing import Sequence, TextIO

from league.reader import InputDataError, parse_iso_date, read_matches
from league.standings import league_table
from league.writer import write_table

EXIT_OK = 0
EXIT_BAD_DATA = 1
EXIT_BAD_ARGS = 2


class _ParserExit(Exception):
    def __init__(self, status: int) -> None:
        super().__init__(status)
        self.status = status


class _Parser(argparse.ArgumentParser):
    """ArgumentParser that writes to injected streams and never calls sys.exit."""

    def __init__(self, *args, out: TextIO, err: TextIO, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._out = out
        self._err = err

    def _print_message(self, message: str, file=None) -> None:
        if message:
            (self._err if file is sys.stderr else self._out).write(message)

    def exit(self, status: int = 0, message: str | None = None):
        if message:
            self._err.write(message)
        raise _ParserExit(status)


def _iso_date(text: str) -> datetime.date:
    try:
        return parse_iso_date(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not a valid YYYY-MM-DD date") from None


def build_parser(out: TextIO, err: TextIO) -> argparse.ArgumentParser:
    parser = _Parser(
        prog="league",
        description=(
            "Calculate a football league table from match results, using the "
            "rules of the English First Division 1974/75 (2 points for a win, "
            "ties broken by goal average)."
        ),
        out=out,
        err=err,
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help="results CSV (date,home_team,home_goals,away_team,away_goals); '-' or omitted reads stdin",
    )
    parser.add_argument(
        "-o", "--output",
        metavar="PATH",
        help="write the table CSV here instead of stdout (parent folders are created)",
    )
    parser.add_argument(
        "--as-at",
        metavar="YYYY-MM-DD",
        type=_iso_date,
        help="only count matches played on or before this date",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    err = stderr if stderr is not None else sys.stderr
    out = stdout if stdout is not None else sys.stdout

    try:
        args = build_parser(out, err).parse_args(argv)
    except _ParserExit as exc:
        return exc.status

    try:
        if args.input == "-":
            source = "<stdin>"
            matches = read_matches(stdin if stdin is not None else _binary_stdin())
        else:
            source = args.input
            with Path(args.input).open(encoding="utf-8-sig", newline="") as f:
                matches = read_matches(f)
    except InputDataError as exc:
        err.write(f"league: error: {source}: {exc}\n")
        return EXIT_BAD_DATA
    except OSError as exc:
        err.write(f"league: error: cannot read input file {args.input!r}: {exc.strerror or exc}\n")
        return EXIT_BAD_ARGS

    table = io.StringIO(newline="")
    write_table(league_table(matches, args.as_at), table)

    if args.output:
        try:
            path = Path(args.output)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8", newline="") as f:
                f.write(table.getvalue())
        except OSError as exc:
            err.write(f"league: error: cannot write output file {args.output!r}: {exc.strerror or exc}\n")
            return EXIT_BAD_ARGS
    else:
        _write_stdout(table.getvalue(), stdout)
    return EXIT_OK


def _binary_stdin() -> TextIO:
    # Re-wrap so the csv module sees raw line endings and a BOM is tolerated.
    return io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8-sig", newline="")


def _write_stdout(text: str, stdout: TextIO | None) -> None:
    if stdout is not None:
        stdout.write(text)
        return
    # Write bytes so Windows doesn't turn "\n" into "\r\n"; output stays LF everywhere.
    sys.stdout.flush()
    sys.stdout.buffer.write(text.encode("utf-8"))
    sys.stdout.buffer.flush()
