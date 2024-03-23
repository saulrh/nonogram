import cpmpy
import pathlib
from rich import print
import cpmpy.expressions.variables
import click
import itertools
import sys
import datetime
import dataclasses
import csv

from nonogram import game
from nonogram import xmlformat


MAX_SOLUTIONS = 1000


@dataclasses.dataclass
class Instance:
    puzzle: game.Puzzle
    model: cpmpy.Model = dataclasses.field(default_factory=cpmpy.Model)
    variables: dict[tuple[game.Dim, int, int], cpmpy.expressions.variables._IntVarImpl] = dataclasses.field(default_factory=dict)
    


def build(puzzle: game.Puzzle):
    instance = Instance(puzzle)

    # let's try the representation where we store the index of each
    # extent.
    for rc, line in instance.puzzle.hints.items():
        for line_idx, hints in enumerate(line):
            for hint_idx, hint in enumerate(hints):
                instance.variables[rc, line_idx, hint_idx] = cpmpy.intvar(0, instance.puzzle.size(rc), name=f"{rc.value}{line_idx}h{hint_idx}")

    # extents can't run off the end of the row
    for rc, line in instance.puzzle.hints.items():
        for line_idx, hints in enumerate(line):
            for hint_idx, hint in enumerate(hints):
                hv = instance.variables[rc, line_idx, hint_idx]
                # if the hint is 2 and the length is 2, then the value
                # must be 0
                instance.model += (hv <= instance.puzzle.size(rc) - hint)

    # adjacent extents have to have a space between them
    for rc, line in instance.puzzle.hints.items():
        for line_idx, hints in enumerate(line):
            for (hint0_idx, hint0), (hint1_idx, hint1) in itertools.pairwise(enumerate(hints)):
                h0v = instance.variables[rc, line_idx, hint0_idx]
                h1v = instance.variables[rc, line_idx, hint1_idx]
                # if h0 is 1 and h0v is 0, then h1v must be 2 or
                # greater. This indicates that this wants < rather
                # than <=.
                instance.model += (h0v + hint0 < h1v)

    # for all spaces in the grid, a row-hint fills that space == a
    # column-hint fills that space
    for row_idx, row_hints in enumerate(instance.puzzle.hints[game.Dim.ROW]):
        for col_idx, col_hints in enumerate(instance.puzzle.hints[game.Dim.COL]):
            row_variables = [instance.variables[game.Dim.ROW, row_idx, i] for i in range(len(row_hints))]
            col_variables = [instance.variables[game.Dim.COL, col_idx, i] for i in range(len(col_hints))]
            row_hint_covers = cpmpy.any((rv + rh > col_idx) & (col_idx >= rv) for rv, rh in zip(row_variables, row_hints))
            col_hint_covers = cpmpy.any((cv + ch > row_idx) & (row_idx >= cv) for cv, ch in zip(col_variables, col_hints))
            instance.model += (
                # if h0v is 0, then h0 of 1 covers column index 0. if
                # h0v is 0, then h0 of 2 covers column index 0 and 1.
                #
                # if h0v is 1, then h0 of 1 covers column index 1. if
                # h0v is 1, then h0 of 2 covers column index 1 and 2.
                row_hint_covers == col_hint_covers
            )


    return instance


def print_solution(stream, instance):
    for row_idx, row_hints in enumerate(instance.puzzle.hints[game.Dim.ROW]):
        for col_idx, col_hints in enumerate(instance.puzzle.hints[game.Dim.COL]):
            row_variables = [instance.variables[game.Dim.ROW, row_idx, i] for i in range(len(row_hints))]
            col_variables = [instance.variables[game.Dim.COL, col_idx, i] for i in range(len(col_hints))]
            row_hint_covers = any(((rv.value() + rh) > col_idx) & (col_idx >= rv.value()) for rv, rh in zip(row_variables, row_hints))
            col_hint_covers = any(((cv.value() + ch) > row_idx) & (row_idx >= cv.value()) for cv, ch in zip(col_variables, col_hints))

            if row_hint_covers:
                stream.write("█")
            else:
                stream.write(" ")
        stream.write("\n")


def make_save_solutions_cb(output_file, instance):
    def save_solutions_cb():
        print_solution(output_file, instance)
        output_file.write("\n")
        output_file.write("\n")
    return save_solutions_cb
    

@click.command
@click.argument('puzzle_file', type=click.File())
@click.option('--save_solutions_file', type=click.File(mode="w"))
def main(puzzle_file, save_solutions_file=None):
    puzzle = xmlformat.load(puzzle_file.read())
    print(f"Puzzle of size {puzzle.rows} x {puzzle.cols}, solving...")
    time_start = datetime.datetime.now(tz=datetime.UTC)
    instance = build(puzzle)
    time_build_done = datetime.datetime.now(tz=datetime.UTC)
    print(f"Model built, took {time_build_done - time_start}")
    has_solution = instance.model.solve()
    if not has_solution:
        raise RuntimeError("No solution found")
    time_solve_done = datetime.datetime.now(tz=datetime.UTC)
    print(f"Solve done, took {time_solve_done - time_start}")
    print_solution(sys.stdout, instance)

    print(f"Counting solutions...")
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


@click.command
def benchmark():
    out = csv.DictWriter(sys.stdout, fieldnames=["puzzle_id", "unique", "time_taken"])
    out.writeheader()

    for p in pathlib.Path('puzzles').iterdir():
        puzzle = xmlformat.load(p.read_text())
        time_start = datetime.datetime.now(tz=datetime.UTC)
        instance = build(puzzle)
        number_of_solutions = instance.model.solveAll(solution_limit=2, time_limit=30 * 60)
        time_end = datetime.datetime.now(tz=datetime.UTC)

        out.writerow({
            'puzzle_id': p,
            "unique": number_of_solutions == 1,
            "time_taken": time_end - time_start,
        })




if __name__ == "__main__":
    main()
