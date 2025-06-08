import more_itertools
import pathlib
from typing import Iterator
import os
import multiprocessing
from rich import print
import rich.progress
import rich.table
import rich.text
import rich.live
import rich.layout
import rich.status
import rich.console
import click
import datetime
import contextlib

from rich_heatmap import heatmap

from nonogram import generate
from nonogram import sampling
from nonogram import solver
from nonogram import solution_db
from nonogram import data
from nonogram import cli_utils


def lower_priority():
    os.nice(10)


def render_progress(existing_data):
    if not existing_data:
        return rich.text.Text("No data")

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
    hm = heatmap.Heatmap(
        cells, colormap=cli_utils.ember_colormap, cell_padding=1, cell_width=5
    )

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
        legend.append("█", style=rich.style.Style(color=cli_utils.ember_colormap(v)))
    legend.append(" 1.0")

    return rich.console.Group(
        "v Size       ◦ #solves          p_filled ->",
        hm,
        legend,
        "",
        progress,
    )


# has to be at module level so it can be called by multiprocessing
def _solve_random_nonograms_internal(
    instance_config: data.InstanceConfig,
) -> data.Solution:
    start = datetime.datetime.now()
    puzzle = generate.generate(instance_config)
    instance = solver.build(puzzle)
    solution_count = instance.model.solveAll(solution_limit=2)
    unique = solution_count == 1
    end = datetime.datetime.now()
    return data.Solution(
        config=instance_config, is_unique=unique, solve_time=end - start
    )


def _solve_random_nonograms(
    sampler: sampling.Sampler,
    threads: int,
    batch: int,
    db: solution_db.SolutionDb,
):
    lower_priority()

    existing_data: dict[data.InstanceConfig, data.SolutionStatistics] = {}

    with (
        multiprocessing.Pool(threads) as pool,
        rich.live.Live(render_progress(existing_data), auto_refresh=False) as live,
    ):
        config_itr: Iterator[data.InstanceConfig] = more_itertools.repeatfunc(
            sampler.sample
        )
        result_itr: Iterator[data.Solution] = pool.imap_unordered(
            _solve_random_nonograms_internal, config_itr, chunksize=1
        )
        batched_itr = more_itertools.ichunked(iterable=result_itr, n=batch)
        for solution_batch in batched_itr:
            db.add_solutions(solutions=solution_batch)
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
@click.option(
    "--db_path", type=click.Path(path_type=pathlib.Path), default="data.sqlite3"
)
def solve_random_nonograms(
    p_min: float,
    p_max: float,
    p_steps: int,
    s_min: int,
    s_max: int,
    threads: int,
    batch: int,
    db_path: pathlib.Path,
):
    with contextlib.closing(solution_db.SolutionDb(db_path)) as db:
        config = data.SamplerConfig(p_min, p_max, p_steps, s_min, s_max)
        _solve_random_nonograms(
            sampling.UniformSampler(config),
            threads,
            batch,
            db,
        )


@click.command
@click.option("--threads", type=int, default=15)
@click.option("--batch", type=int, default=10)
@click.option(
    "--db_path", type=click.Path(path_type=pathlib.Path), default="data.sqlite3"
)
def continue_random_nonograms(threads: int, batch: int, db_path: pathlib.Path):
    with contextlib.closing(solution_db.SolutionDb(db_path)) as db:
        sampler_config, unmatched_probs, extra_probs = db.infer_config()
        existing_data = db.get_stats()

        if unmatched_probs != 0 or extra_probs != 0:
            print("Failed to infer sampler configuration.")
            print("  Best hypothesis: ", sampler_config)
            print(
                f"  Failed to generated {unmatched_probs} values of p and {extra_probs} supernumerary values"
            )
            exit(1)

        print("Inferred following configuration: ", sampler_config)

        _solve_random_nonograms(
            sampling.FillGapsSampler(sampler_config, existing_data),
            threads,
            batch,
            db,
        )
