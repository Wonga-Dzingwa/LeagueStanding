# CLAUDE.md

Command-line app that works out a football league table from match results in a CSV file.
Target run: English First Division 1974/75, gameweek 10 (SPAN BE coding test).

## Tech stack
- Python 3.10+, standard library only (`csv`, `argparse`, `dataclasses`, `pathlib`).
- Tests: pytest (the only dev dependency, listed in `requirements-dev.txt`; never commit a venv).
- **Ask before adding any dependency.**

## League rules (1974/75, verified against Wikipedia)
- A win is 2 points, a draw 1, a loss 0.
- Rank by: 1) points, 2) goal average (goals for ÷ goals against), 3) goals scored,
  4) team name A–Z (our choice, so the order is always the same).
- Use goal average, never goal difference (goal difference started in 1976/77).
- If goals against is 0, goal average counts as higher than any real ratio (∞).
  If goals for and against are both 0, it counts as 1.0.
- Compare goal average exactly with `fractions.Fraction`, never floats. Handle ∞ in the
  sort key, e.g. a `(is_infinite, Fraction)` tuple.

## Data
- Source: engsoccerdata (James P. Curley, DOI 10.5281/zenodo.13158), free for non-commercial use with a citation.
- `data/results_1974_75_full.csv`: 462 matches. `data/results_1974_75_week10.csv`: 107 matches.
- Columns: `date,home_team,home_goals,away_team,away_goals` (dates as ISO `YYYY-MM-DD`).
- **Gameweek 10 means all matches up to and including 1974-09-28.** Six clubs (Arsenal, Leeds,
  Leicester, Middlesbrough, Newcastle, Tottenham) have played 9 games at that point and the rest 10.
  This is correct: they missed the 24–25 Sep midweek round, and no cutoff gives every club 10 games.
- Sanity check: the full season must put Derby County first on 53 points, with Liverpool above Ipswich on goal average.

## I/O
- Read a file path or stdin; write a CSV table to a file path or stdout.
- Filter by date with `--as-at YYYY-MM-DD`.
- Output columns: `Pos,Team,P,W,D,L,GF,GA,GAvg,Pts`.
- Show GAvg to 3 decimal places (e.g. `1.367`), and `-` when GA is 0. This is display only;
  ranking uses the exact value.
- Generated tables go in `data/output/` and are committed (the submission must include them).
- A bad CSV row stops the run: fail with the line number and the reason, and never skip it.
  Decode input as bytes in one go so an invalid UTF-8 byte is reported on its real line.
- Team names that differ only in upper/lower case (`Everton` / `everton`) are bad data (exit 1).
- Exit codes: `0` for ok, `1` for bad input data, `2` for bad arguments (argparse's default).
  A missing or unreadable input file, or an unwritable output path, counts as a bad argument (2).
  `3` for an unexpected internal error (a bug): one line on stderr, no traceback, no output.
- Run with `python -m league [INPUT|-] [-o PATH] [--as-at YYYY-MM-DD]`.
- No INPUT and stdin is a terminal: print usage and exit 2, never wait. An explicit `-` still reads stdin.
- Errors and warnings go to stderr only; stdout carries nothing but the CSV table.
- If `--as-at` leaves no matches, warn on stderr but still exit 0 (the header-only table is valid).

## Cross-platform (developed on Windows, run on macOS)
- Use `pathlib` for paths; never hard-code `\` or drive letters.
- Open files with `encoding="utf-8"`, and pass `newline=""` for the csv module.
- Line endings are LF: keep `.gitattributes` with `* text=auto eol=lf`.
- Commands in docs are POSIX (`python3`, `./`), and scripts have no Windows-only features.
- Nothing may depend on the locale (decimal separators, date parsing).

## How we work
- Take small steps: one focused change at a time.
- Every change comes with tests, both for new behaviour and for bugs being fixed.
- Run `python -m pytest` after each step and report the result honestly.
- End each step with a suggested commit message. Don't commit unless asked.
- Other SPAN candidates' repos must never be used as a reference.
