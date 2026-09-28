# League Standings: English First Division 1974/75

A command-line application that calculates a football league table from a CSV of match
results. It uses the rules of the English First Division in the 1974/75 season.
It is applied to **gameweek 10 of 1974/75**, and the result is committed in
[`data/output/standings_1974_75_week10.csv`](data/output/standings_1974_75_week10.csv).

## Requirements

- Python 3.10 or newer (`python3 --version`). The app uses only the standard library.
- To run the tests you also need pytest, the only dev dependency.

## Setup

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt   # only needed for the tests
```

## Usage

```sh
python3 -m league [INPUT | -] [-o PATH] [--as-at YYYY-MM-DD]
```

| Argument | Meaning |
|---|---|
| `INPUT` | Results CSV. Omit it or pass `-` to read from stdin. |
| `-o PATH` | Write the table to `PATH` (parent folders are created). By default it is written to stdout. |
| `--as-at DATE` | Only count matches played on or before `DATE`. |

Generate the gameweek 10 table (this is how the committed output was produced):

```sh
python3 -m league data/results_1974_75_week10.csv -o data/output/standings_1974_75_week10.csv
```

The same table comes from the full season with a date cutoff:

```sh
python3 -m league data/results_1974_75_full.csv --as-at 1974-09-28
```

stdin and stdout work too:

```sh
cat data/results_1974_75_full.csv | python3 -m league > final_table.csv
```

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Success. |
| `1` | Bad input data. The first bad row stops the run, and stderr names the file, line number and reason. |
| `2` | Bad arguments: an unknown option, an invalid `--as-at` date, an input file that can't be read, or an output path that can't be written. |

Errors only go to stderr. On any failure nothing is written to stdout and no output file is created.

## Input format

A UTF-8 CSV file with a header row and one match per line:

```csv
date,home_team,home_goals,away_team,away_goals
1974-08-17,Everton,0,Derby County,0
1974-08-17,Chelsea,0,Carlisle United,2
```

A row is rejected if it has:
- the wrong number of columns
- a blank team name
- a team playing itself
- goals that aren't whole numbers of 0 or more
- a date that isn't in `YYYY-MM-DD` form
- a blank line
- the same home-and-away fixture as an earlier row

Rows are never skipped silently. A UTF-8 BOM and CRLF line endings are accepted.

## Output format

```csv
Pos,Team,P,W,D,L,GF,GA,GAvg,Pts
1,Ipswich Town,10,8,0,2,18,6,3.000,16
```

The columns are position, team, played, won, drawn, lost, goals for, goals against,
goal average and points. `GAvg` is shown to 3 decimal places, or as `-` when a team
hasn't conceded. The file always uses LF line endings.

## League rules (1974/75)

| Rule | 1974/75 | Note |
|---|---|---|
| Points | Win 2, draw 1, loss 0 | Three points for a win started in 1981/82 |
| Ties on points | **Goal average** (goals for ÷ goals against), then goals scored | Goal difference replaced goal average in 1976/77 |

Some behaviour isn't covered by the historical rules, so we chose it:
- **Goal average is compared exactly**, using `fractions.Fraction`, never floating point.
- **A team with no goals against** has an infinite goal average, which ranks above any real ratio. A team that has neither scored nor conceded counts as 1.0.
- **Final tie-break:** team name A–Z, so the output order is always the same and positions are never shared.

Goal average changes the real 1974/75 final table. Liverpool and Ipswich both finished on 51 points. Ipswich had the better goal difference (+22 v +21), but Liverpool's goal average of 60/39 = 1.538 beat Ipswich's 66/44 = 1.500, so Liverpool finished second. The acceptance tests check this.

## What "gameweek 10" means

"The 10th week" isn't defined precisely, so we treat it as **gameweek 10: every match up to
and including Saturday 28 September 1974**, when the 10th round of fixtures was completed.
That's 107 matches.

Unlike a modern fixture list, **not every club has played 10 games**:

| Games played | Clubs |
|---|---|
| 10 | 16 clubs |
| 9 | Arsenal, Leeds United, Leicester City, Middlesbrough, Newcastle United, Tottenham Hotspur |

Those six clubs didn't play in the midweek round of 24–25 September 1974, which had
only 8 matches instead of 11. There is no cutoff that leaves every club on 10 games:
the six play their 10th match on 5 October, but four of them play clubs that then reach 11.
So the table is shown as it actually stood on that date, as real league tables are.
You can choose a different cutoff with `--as-at`.

## Gameweek 10 table (after 28 September 1974)

| Pos | Team | P | W | D | L | GF | GA | GAvg | Pts |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | Ipswich Town | 10 | 8 | 0 | 2 | 18 | 6 | 3.000 | 16 |
| 2 | Manchester City | 10 | 6 | 2 | 2 | 14 | 11 | 1.273 | 14 |
| 3 | Liverpool | 10 | 6 | 1 | 3 | 17 | 8 | 2.125 | 13 |
| 4 | Everton | 10 | 4 | 5 | 1 | 14 | 11 | 1.273 | 13 |
| 5 | Sheffield United | 10 | 5 | 3 | 2 | 14 | 14 | 1.000 | 13 |
| 6 | Newcastle United | 9 | 5 | 2 | 2 | 16 | 13 | 1.231 | 12 |
| 7 | Middlesbrough | 9 | 4 | 3 | 2 | 12 | 7 | 1.714 | 11 |
| 8 | Derby County | 10 | 3 | 5 | 2 | 16 | 13 | 1.231 | 11 |
| 9 | Stoke City | 10 | 4 | 3 | 3 | 13 | 11 | 1.182 | 11 |
| 10 | Wolverhampton Wanderers | 10 | 3 | 5 | 2 | 12 | 11 | 1.091 | 11 |
| 11 | Carlisle United | 10 | 4 | 2 | 4 | 8 | 8 | 1.000 | 10 |
| 12 | West Ham United | 10 | 4 | 1 | 5 | 20 | 18 | 1.111 | 9 |
| 13 | Burnley | 10 | 4 | 1 | 5 | 17 | 18 | 0.944 | 9 |
| 14 | Birmingham City | 10 | 3 | 2 | 5 | 12 | 17 | 0.706 | 8 |
| 15 | Coventry City | 10 | 2 | 4 | 4 | 11 | 17 | 0.647 | 8 |
| 16 | Leicester City | 9 | 2 | 3 | 4 | 13 | 17 | 0.765 | 7 |
| 17 | Luton Town | 10 | 1 | 5 | 4 | 11 | 16 | 0.688 | 7 |
| 18 | Chelsea | 10 | 2 | 3 | 5 | 10 | 18 | 0.556 | 7 |
| 19 | Leeds United | 9 | 2 | 2 | 5 | 12 | 14 | 0.857 | 6 |
| 20 | Arsenal | 9 | 2 | 2 | 5 | 9 | 12 | 0.750 | 6 |
| 21 | Tottenham Hotspur | 9 | 3 | 0 | 6 | 11 | 15 | 0.733 | 6 |
| 22 | Queens Park Rangers | 10 | 1 | 4 | 5 | 8 | 13 | 0.615 | 6 |

## Tests

```sh
python3 -m pytest
```

| File | Covers |
|---|---|
| `tests/test_rules.py` | Points, exact goal average, and each tie-break level |
| `tests/test_reader.py` | Valid input and every rejected row type, with its line number |
| `tests/test_standings.py` | Building team records, invariants, date cutoff |
| `tests/test_writer.py` | Output layout, 3-decimal rounding, LF line endings |
| `tests/test_cli.py` | stdin/stdout/files, exit codes, stderr, real `python -m league` runs |
| `tests/test_acceptance.py` | Real data: the 1974/75 final table, the gameweek 10 table, and a byte-for-byte check against the committed output |

If a change alters the table on purpose, regenerate the committed output with the command
in [Usage](#usage). The acceptance test will fail until you do.

## Project layout

```
league/            the application (python3 -m league)
  rules.py         1974/75 points and ranking rules (the only season-specific code)
  reader.py        strict CSV reader
  standings.py     date filter, team records, ranking
  writer.py        CSV output
  cli.py           arguments, exit codes, error reporting
tests/             pytest suite
data/              input results (full season and gameweek 10)
data/output/       generated standings table
CLAUDE.md          instructions for the AI assistant
.claude/           Claude Code project settings
```

## Data source

The match results come from **engsoccerdata** by James P. Curley
(<https://github.com/jalapic/engsoccerdata>, file `data-raw/england.csv`).
We used the rows with `Season == 1974` and `division == 1`, keeping the date, teams and goals.
Citation: *James P. Curley (2016). engsoccerdata: English Soccer Data 1871–2016.
DOI 10.5281/zenodo.13158.* The dataset is free for non-commercial use with this citation.

The full-season data reproduces the published 1974/75 final table (Derby County champions on
53 points; Luton Town, Chelsea and Carlisle United relegated).

Sources for the rules: Wikipedia, *1974–75 Football League First Division*, *1974–75 in English
football* and *1976–77 in English football*.
