import dataclasses
import enum
import csv
import multiprocessing
import pathlib
import rich.progress
import rich.table
import rich.text
import rich.live
import rich.layout
import rich.status
import rich.console
from rich import print
import click
import sys
import datetime
import contextlib
import natsort
import cmasher  # noqa: F401
from typing import Callable, Iterable, Optional

from nonogram import xmlformat
from nonogram import cli_utils
from nonogram import solver


class Format(enum.Enum):
    RICH = enum.auto()
    RICH_STATIC = enum.auto()
    CSV = enum.auto()


class SortBy(enum.Enum):
    NONE = enum.auto()
    ID = enum.auto()
    TIME = enum.auto()


@dataclasses.dataclass
class Row:
    path: pathlib.Path
    columns: int
    rows: int
    num_solutions: int
    time_taken: datetime.timedelta


MAX_SOLUTIONS = 10


def _internal(p: pathlib.Path) -> Optional[Row]:
    try:
        puzzle = xmlformat.load(p.read_text())
    except NotImplementedError:
        return None
    time_start = datetime.datetime.now(tz=datetime.UTC)
    instance = solver.build(puzzle)
    num_solutions = instance.model.solveAll(
        solution_limit=MAX_SOLUTIONS, time_limit=30 * 60
    )
    time_end = datetime.datetime.now(tz=datetime.UTC)
    return Row(
        path=p,
        columns=puzzle.n_cols,
        rows=puzzle.n_rows,
        num_solutions=num_solutions,
        time_taken=time_end - time_start,
    )


Sorter = Callable[[Iterable[Row]], list[Row]]


@contextlib.contextmanager
def make_csv_writer(sorter: Sorter):
    out = csv.DictWriter(
        sys.stdout,
        fieldnames=["puzzle_id", "width", "height", "is_unique", "time_taken"],
    )

    rows = []

    def write_row(row: Row):
        rows.append(row)

    yield write_row

    for row in sorter(rows):
        out.writerow(
            {
                "puzzle_id": row.path.name,
                "width": row.columns,
                "height": row.rows,
                "is_unique": str(row.num_solutions == 1),
                "time_taken": str(row.time_taken.total_seconds()),
            }
        )


UNIQUE_STYLE = rich.style.Style(color="green")
FAIL_STYLE = rich.style.Style(color="red")
NON_UNIQUE_STYLE = rich.style.Style(color="yellow")


def make_table(from_rows):
    table = rich.table.Table()
    table.add_column("Puzzle ID", justify="right")
    table.add_column("Width", justify="right")
    table.add_column("Height", justify="right")
    table.add_column("#Solutions", justify="center")
    table.add_column("Time Taken", justify="right")

    if from_rows:
        min_time = min(r.time_taken for r in from_rows)
        max_time = max(r.time_taken for r in from_rows)
    else:
        min_time = None
        max_time = None

    for row in from_rows:
        if min_time != max_time:
            v = (row.time_taken - min_time) / (max_time - min_time)

        else:
            v = 0.5
        time_style = rich.style.Style(color=cli_utils.horizon_colormap(v))
        if row.num_solutions == 1:
            num_solutions_text = rich.text.Text("UNIQUE", UNIQUE_STYLE)
        elif row.num_solutions == 0:
            num_solutions_text = rich.text.Text("NO SOLUTION", FAIL_STYLE)
        elif row.num_solutions == MAX_SOLUTIONS:
            num_solutions_text = rich.text.Text(f">{row.num_solutions}", FAIL_STYLE)
        else:
            num_solutions_text = rich.text.Text(
                f"{row.num_solutions}", NON_UNIQUE_STYLE
            )

        table.add_row(
            rich.text.Text(row.path.name),
            rich.text.Text(str(row.columns)),
            rich.text.Text(str(row.rows)),
            num_solutions_text,
            rich.text.Text(str(row.time_taken), time_style),
        )
    return table


@contextlib.contextmanager
def make_rich_writer(sorter: Sorter):
    status = rich.status.Status("Running...")
    with rich.live.Live(
        make_table([]), refresh_per_second=10, vertical_overflow="visible"
    ) as live:
        rows = []

        def write_row(row: Row):
            rows.append(row)
            live.update(
                rich.console.Group(
                    make_table(sorter(rows)),
                    status,
                )
            )

        yield write_row
    status.stop()
    print("Done!")


@contextlib.contextmanager
def make_rich_static_writer(sorter: Sorter):
    rows = []

    def write_row(row: Row):
        rows.append(row)

    yield write_row
    print(make_table(sorter(rows)))


def by_id_sorter(solutions: Iterable[Row]) -> list[Row]:
    return list(natsort.natsorted(solutions, key=lambda solution: solution.path))


def by_time_sorter(solutions: Iterable[Row]) -> list[Row]:
    return list(sorted(solutions, key=lambda solution: solution.time_taken))


def none_sorter(solutions: Iterable[Row]) -> list[Row]:
    return list(solutions)


@click.command
@click.option(
    "--format", type=click.Choice(Format, case_sensitive=False), default=Format.RICH
)
@click.option(
    "--sort_by", type=click.Choice(SortBy, case_sensitive=False), default=SortBy.NONE
)
@click.option(
    "--puzzle_dir",
    type=click.Path(
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        path_type=pathlib.Path,
    ),
    default="puzzles",
)
@click.option("--threads", type=int, default=20)
def main(format: Format, sort_by: SortBy, threads: int, puzzle_dir: pathlib.Path):
    files = list(puzzle_dir.iterdir())

    if format == Format.CSV:
        make_writer_fn = make_csv_writer
    elif format == Format.RICH:
        make_writer_fn = make_rich_writer
    elif format == Format.RICH_STATIC:
        make_writer_fn = make_rich_static_writer

    if sort_by == SortBy.ID:
        sorter = by_id_sorter
    elif sort_by == SortBy.TIME:
        sorter = by_time_sorter
    elif sort_by == SortBy.NONE:
        sorter = none_sorter

    with make_writer_fn(sorter) as write_cb, multiprocessing.Pool(threads) as pool:
        solns = pool.imap_unordered(_internal, files)
        for soln in filter(None, solns):
            write_cb(soln)
