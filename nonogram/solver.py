import cpmpy
import cpmpy.expressions.variables
import click
import itertools
import sys
import datetime
import dataclasses

from nonogram import game
from nonogram import xmlformat


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


def print_solution(instance):
    for row_idx, row_hints in enumerate(instance.puzzle.hints[game.Dim.ROW]):
        for col_idx, col_hints in enumerate(instance.puzzle.hints[game.Dim.COL]):
            row_variables = [instance.variables[game.Dim.ROW, row_idx, i] for i in range(len(row_hints))]
            col_variables = [instance.variables[game.Dim.COL, col_idx, i] for i in range(len(col_hints))]
            row_hint_covers = any(((rv.value() + rh) > col_idx) & (col_idx >= rv.value()) for rv, rh in zip(row_variables, row_hints))
            col_hint_covers = any(((cv.value() + ch) > row_idx) & (row_idx >= cv.value()) for cv, ch in zip(col_variables, col_hints))

            if row_hint_covers:
                sys.stdout.write("X")
            else:
                sys.stdout.write(".")
        sys.stdout.write("\n")
    

@click.command
@click.argument('puzzle', type=click.File())
def main(puzzle):
    puzzle = xmlformat.load(puzzle.read())
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
    print_solution(instance)

    


if __name__ == "__main__":
    main()
