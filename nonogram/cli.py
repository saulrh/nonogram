import more_itertools
from typing import Optional
import csv
import os
import multiprocessing
from rich import print
import pathlib
import rich.progress
import rich.table
import rich.text
import click
import sys
import datetime
import contextlib
import itertools

from nonogram import generate
from nonogram import xmlformat
from nonogram import solver
from nonogram import solution_db

MAX_SOLUTIONS = 1000


def lowpriority():
    os.nice(10)


def make_save_solutions_cb(output_file, instance):
    def save_solutions_cb():
        solver.print_solution(output_file, instance)
        output_file.write("\n")
        output_file.write("\n")

    return save_solutions_cb


@click.command
@click.argument("puzzle_file", type=click.File())
@click.option("--save_solutions_file", type=click.File(mode="w"))
def main(puzzle_file, save_solutions_file=None):
    puzzle = xmlformat.load(puzzle_file.read())
    print(f"Puzzle of size {puzzle.rows} x {puzzle.cols}, solving...")
    time_start = datetime.datetime.now(tz=datetime.UTC)
    instance = solver.build(puzzle)
    time_build_done = datetime.datetime.now(tz=datetime.UTC)
    print(f"Model built, took {time_build_done - time_start}")
    has_solution = instance.model.solve()
    if not has_solution:
        raise RuntimeError("No solution found")
    time_solve_done = datetime.datetime.now(tz=datetime.UTC)
    print(f"Solve done, took {time_solve_done - time_start}")
    solver.print_solution(sys.stdout, instance)

    print("Counting solutions...")
    if save_solutions_file:
        cb = make_save_solutions_cb(
            save_solutions_file,
            instance,
        )
    else:
        cb = None
    number_of_solutions = instance.model.solveAll(
        display=cb,
        solution_limit=MAX_SOLUTIONS,
    )
    time_proof_done = datetime.datetime.now(tz=datetime.UTC)
    if number_of_solutions == 1:
        color = "green"
    elif number_of_solutions == MAX_SOLUTIONS:
        color = "red"
    else:
        color = "yellow"
    print(f"[{color}]Found {number_of_solutions} solutions")
    print(f"Proof done, took {time_proof_done - time_solve_done}")


def _probability_internal(config):
    start = datetime.datetime.now()
    puzzle = config.generate()
    instance = solver.build(puzzle)
    solution_count = instance.model.solveAll(solution_limit=2)
    unique = solution_count == 1
    end = datetime.datetime.now()
    dt = (end - start).total_seconds()
    return solution_db.Solution(config=config, is_unique=unique, runtime=dt)


class NCompleteColumn(rich.progress.ProgressColumn):
    def __init__(self, table_column: Optional[rich.table.Column] = None):
        super().__init__(table_column=table_column)

    def render(self, task: "rich.progress.Task") -> rich.text.Text:
        completed = int(task.completed)
        return rich.text.Text(
            f"{completed:d}",
            style="progress.download",
        )


class CompletionRateColumn(rich.progress.ProgressColumn):
    def render(self, task: "rich.progress.Task") -> rich.text.Text:
        speed = task.finished_speed or task.speed
        if speed is None:
            return rich.text.Text("?", style="progress.data.speed")
        return rich.text.Text(f"{speed:.3f}/s", style="progress.data.speed")


def _solve_random_nonograms(
    config: generate.SampleConfig,
    threads: int,
    batch: int,
):
    lowpriority()
    with (
        multiprocessing.Pool(threads) as pool,
        rich.progress.Progress(
            rich.progress.TextColumn("[progress.description]{task.description}"),
            NCompleteColumn(),
            CompletionRateColumn(),
            rich.progress.TimeElapsedColumn(),
            rich.progress.SpinnerColumn(),
            speed_estimate_period=datetime.timedelta(minutes=10).total_seconds(),
        ) as prog,
        contextlib.closing(solution_db.SolutionDb()) as db,
    ):
        existing_data = db.get_stats()
        init_total = db.get_solution_count() or 0
        solve_task = prog.add_task(
            "Solving...", completed=init_total, start=True, total=None
        )

        config_itr = more_itertools.repeatfunc(
            config.uniform,
        )
        result_itr = pool.imap_unordered(_probability_internal, config_itr, chunksize=1)
        for batch in itertools.batched(result_itr, batch):
            db.add_solutions(batch)
            prog.update(solve_task, advance=len(batch))


@click.command
@click.option("--p_min", type=float)
@click.option("--p_max", type=float)
@click.option("--p_steps", type=int)
@click.option("--s_min", type=int)
@click.option("--s_max", type=int)
@click.option("--threads", type=int, default=5)
@click.option("--batch", type=int, default=1)
def random_nonogram(
    p_min: float,
    p_max: float,
    p_steps: int,
    s_min: int,
    s_max: int,
    threads: int,
    batch: int,
):
    _solve_random_nonograms(
        generate.SampleConfig(p_min, p_max, p_steps, s_min, s_max),
        threads,
        batch,
    )


@click.command
@click.option("--threads", type=int, default=5)
@click.option("--batch", type=int, default=1)
def continue_random_nonogram(threads: int, batch: int):
    with contextlib.closing(solution_db.SolutionDb()) as db:
        config, unmatched_probs, extra_probs = db.infer_config()
    if unmatched_probs != 0 or extra_probs != 0:
        print(config, unmatched_probs, extra_probs)
        exit(1)

    print("continuing with following configuration: ", config)

    _solve_random_nonograms(
        config,
        threads,
        batch,
    )


@click.command
def benchmark():
    out = csv.DictWriter(sys.stdout, fieldnames=["puzzle_id", "unique", "time_taken"])
    out.writeheader()

    for p in pathlib.Path("puzzles").iterdir():
        puzzle = xmlformat.load(p.read_text())
        time_start = datetime.datetime.now(tz=datetime.UTC)
        instance = solver.build(puzzle)
        number_of_solutions = instance.model.solveAll(
            solution_limit=2, time_limit=30 * 60
        )
        time_end = datetime.datetime.now(tz=datetime.UTC)

        out.writerow(
            {
                "puzzle_id": p,
                "unique": number_of_solutions == 1,
                "time_taken": time_end - time_start,
            }
        )
