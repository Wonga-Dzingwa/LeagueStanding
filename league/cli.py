"""Command-line entry point.

Exit codes: 0 ok, 1 bad input data, 2 bad arguments (including an unreadable input file),
3 unexpected internal error. Errors go to stderr; stdout carries only the CSV table.
"""

from __future__ import annotations

import argparse
import datetime
import io
import sys
from pathlib import Path
from typing import BinaryIO, Sequence, TextIO

from league.reader import InputDataError, parse_iso_date, read_matches_bytes
from league.standings import filter_as_at, league_table
from league.writer import write_table

EXIT_OK = 0
EXIT_BAD_DATA = 1
EXIT_BAD_ARGS = 2
EXIT_INTERNAL = 3


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
        default=None,
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
    stdin: BinaryIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    err = stderr if stderr is not None else sys.stderr
    out = stdout if stdout is not None else sys.stdout

    parser = build_parser(out, err)
    try:
        args = parser.parse_args(argv)
    except _ParserExit as exc:
        return exc.status

    try:
        return _run(args, parser, stdin, stdout, err)
    except Exception as exc:  # anything not handled above is a bug, not bad input
        err.write(f"league: internal error: {type(exc).__name__}: {exc}\n")
        return EXIT_INTERNAL


def _run(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
    stdin: BinaryIO | None,
    stdout: TextIO | None,
    err: TextIO,
) -> int:
    if args.input in (None, "-"):
        stream = stdin if stdin is not None else getattr(sys.stdin, "buffer", None)
        # No input named and nothing piped in: don't sit waiting for keyboard input.
        # An explicit "-" still reads from a terminal, as Unix tools do.
        if stream is None or (args.input is None and stream.isatty()):
            err.write(parser.format_usage())
            err.write("league: error: no input: give a results CSV file, or pipe one in on stdin\n")
            return EXIT_BAD_ARGS

    try:
        if args.input in (None, "-"):
            source = "<stdin>"
            data = stream.read()
        else:
            source = args.input
            data = Path(args.input).read_bytes()
        matches = read_matches_bytes(data)
    except InputDataError as exc:
        err.write(f"league: error: {source}: {exc}\n")
        return EXIT_BAD_DATA
    except OSError as exc:
        err.write(f"league: error: cannot read input file {args.input!r}: {exc.strerror or exc}\n")
        return EXIT_BAD_ARGS

    table = io.StringIO(newline="")
    kept = filter_as_at(matches, args.as_at)
    if args.as_at is not None and not kept:
        err.write(
            f"league: warning: no matches on or before {args.as_at.isoformat()}; "
            "the table is empty\n"
        )
    write_table(league_table(kept), table)

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


def _write_stdout(text: str, stdout: TextIO | None) -> None:
    if stdout is not None:
        stdout.write(text)
        return
    # Write bytes so Windows doesn't turn "\n" into "\r\n"; output stays LF everywhere.
    sys.stdout.flush()
    sys.stdout.buffer.write(text.encode("utf-8"))
    sys.stdout.buffer.flush()
