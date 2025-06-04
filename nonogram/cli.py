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

from nonogram import generate
from nonogram import xmlformat
from nonogram import solver
from nonogram import solution_db

MAX_SOLUTIONS = 1000


def lowpriority():
    os.nice(10)


def make_save_solutions_cb(output_file, instance):
    def save_solutions_cb():
        print_solution(output_file, instance)
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
    print_solution(sys.stdout, instance)

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


def _probability_internal(arg):
    s, p = arg
    start = datetime.datetime.now()
    puzzle = generate.random_puzzle(probability=p, size=s)
    instance = solver.build(puzzle)
    solution_count = instance.model.solveAll(solution_limit=2)
    unique = solution_count == 1
    end = datetime.datetime.now()
    dt = (end - start).total_seconds()
    return (s, p, unique, dt)


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


@click.command
@click.option("--p_min", type=float)
@click.option("--p_max", type=float)
@click.option("--p_steps", type=int)
@click.option("--s_min", type=int)
@click.option("--s_max", type=int)
def probability(p_min: float, p_max: float, p_steps: int, s_min: int, s_max: int):
    lowpriority()

    solution_db.init()

    with (
        multiprocessing.Pool(5) as pool,
        rich.progress.Progress(
            rich.progress.TextColumn("[progress.description]{task.description}"),
            NCompleteColumn(),
            CompletionRateColumn(),
            rich.progress.TimeElapsedColumn(),
            rich.progress.SpinnerColumn(),
            speed_estimate_period=datetime.timedelta(minutes=10).total_seconds(),
        ) as prog,
    ):
        init_total = solution_db.get_solution_count()
        solve_task = prog.add_task(
            "Solving...", completed=init_total, start=True, total=None
        )

        param_itr = more_itertools.repeatfunc(
            generate.sample_config_uniform, None, p_min, p_max, p_steps, s_min, s_max
        )
        result_itr = pool.imap_unordered(_probability_internal, param_itr, chunksize=1)
        for r_s, r_p, r_unique, r_dt in result_itr:
            solution_db.add_solution(prob=r_p, size=r_s, uniq=r_unique, runtime=r_dt)
            prog.update(solve_task, advance=1)


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
