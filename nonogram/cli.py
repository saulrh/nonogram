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
import rich.live
import rich.layout
import rich.status
import rich.console
import click
import sys
import datetime
import contextlib
import matplotlib
import cmasher  # noqa: F401

from rich_heatmap import heatmap

from nonogram import generate
from nonogram import sampling
from nonogram import xmlformat
from nonogram import solver
from nonogram import solution_db
from nonogram import data

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


def _probability_internal(instance_config: data.InstanceConfig):
    start = datetime.datetime.now()
    puzzle = generate.generate(instance_config)
    instance = solver.build(puzzle)
    solution_count = instance.model.solveAll(solution_limit=2)
    unique = solution_count == 1
    end = datetime.datetime.now()
    dt = (end - start).total_seconds()
    return data.Solution(config=instance_config, is_unique=unique, runtime=dt)


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
    sampler: sampling.Sampler,
    threads: int,
    batch: int,
):
    lowpriority()

    with (
        multiprocessing.Pool(threads) as pool,
        contextlib.closing(solution_db.SolutionDb()) as db,
    ):
        existing_data = db.get_stats()

        with rich.live.Live(render_progress(existing_data), auto_refresh=False) as live:
            config_itr = more_itertools.repeatfunc(sampler.sample)
            result_itr = pool.imap_unordered(
                _probability_internal, config_itr, chunksize=1
            )
            for batch in more_itertools.ichunked(result_itr, batch):
                db.add_solutions(batch)
                existing_data = db.get_stats()
                live.update(render_progress(existing_data), refresh=True)


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
    config = data.SamplerConfig(p_min, p_max, p_steps, s_min, s_max)
    _solve_random_nonograms(
        sampling.UniformSampler(config),
        threads,
        batch,
    )


COLORMAP = matplotlib.colormaps["cmr.ember"]


def render_progress(existing_data):
    cells = []
    for instance, solutions in existing_data.items():
        cells.append(
            heatmap.HeatmapCell(
                instance.size,
                instance.prob,
                solutions.unique / solutions.total,
                text=str(solutions.total),
            )
        )
    hm = heatmap.Heatmap(cells, colormap=colormap, cell_padding=1, cell_width=5)

    total_runs = sum(d.total for d in existing_data.values())
    total_runtime = sum(
        (d.runtime for d in existing_data.values()), start=datetime.timedelta()
    )

    progress = rich.text.Text.assemble(
        "Solving...   ",
        " ",
        (str(total_runs), "green"),
        " solves, ",
        (str(total_runtime), "yellow"),
        " CPU time",
    )
    legend = rich.text.Text()
    legend.append("   p_unique   0.0 ")
    for i in range(100):
        v = i / 100
        legend.append("█", style=rich.style.Style(color=colormap(v)))
    legend.append(" 1.0")

    return rich.console.Group(
        "v Size       ◦ #solves          p_filled ->",
        hm,
        legend,
        "",
        progress,
    )


def colormap(value: float) -> tuple[float, float, float]:
    rgba = COLORMAP(value)
    return rich.color.Color.from_rgb(
        255 * rgba[0],
        255 * rgba[1],
        255 * rgba[2],
    )


@click.command
@click.option("--threads", type=int, default=5)
@click.option("--batch", type=int, default=1)
def continue_random_nonogram(threads: int, batch: int):
    with contextlib.closing(solution_db.SolutionDb()) as db:
        sampler_config, unmatched_probs, extra_probs = db.infer_config()
        existing_data = db.get_stats()

    if unmatched_probs != 0 or extra_probs != 0:
        print(config, unmatched_probs, extra_probs)
        exit(1)

    print("continuing with following configuration: ", sampler_config)

    print(make_heatmap(existing_data))

    _solve_random_nonograms(
        sampling.FillGapsSampler(sampler_config, existing_data),
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
