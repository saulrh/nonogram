import cpmpy
import cpmpy.expressions.variables
import itertools
import dataclasses
import datetime
import time

from nonogram import game
from nonogram import data


@dataclasses.dataclass
class Instance:
    puzzle: game.Puzzle
    model: cpmpy.solvers.ortools.CPM_ortools
    build_time: datetime.timedelta = datetime.timedelta()
    variables: dict[
        tuple[game.Dim, int, int], cpmpy.expressions.variables._IntVarImpl
    ] = dataclasses.field(default_factory=dict)

    def solve(self, test_uniqueness: bool) -> data.Solution:
        time_solve_start = time.process_time()
        has_solution = self.model.solve()
        time_solve_end = time.process_time()
        solve_time = datetime.timedelta(seconds=time_solve_end - time_solve_start)
        if not has_solution:
            raise RuntimeError("No solution found")

        if test_uniqueness:
            num_solutions = self.model.solveAll(solution_limit=2)
        else:
            num_solutions = 0

        return data.Solution(
            is_unique=num_solutions == 1,
            solve_time=solve_time,
            grid=self.extract_grid(),
            config=self.puzzle.config,
        )

    def solve_all(self, solution_limit: int) -> data.Solutions:
        grids = []

        def solution_cb():
            grids.append(self.extract_grid())

        time_solve_start = time.process_time()
        self.model.solveAll(display=solution_cb, solution_limit=solution_limit)
        time_solve_end = time.process_time()
        solve_all_time = datetime.timedelta(seconds=time_solve_end - time_solve_start)

        return data.Solutions(
            solve_all_time=solve_all_time,
            grids=grids,
        )

    def extract_grid(self) -> list[list[bool]]:
        result = []
        for row_idx, row_hints in enumerate(self.puzzle.hints[game.Dim.ROW]):
            row = []
            for col_idx, col_hints in enumerate(self.puzzle.hints[game.Dim.COL]):
                row_variables = [
                    self.variables[game.Dim.ROW, row_idx, i]
                    for i in range(len(row_hints))
                ]
                row_hint_covers = any(
                    ((rv.value() + rh) > col_idx) & (col_idx >= rv.value())
                    for rv, rh in zip(row_variables, row_hints)
                )

                row.append(row_hint_covers)
            result.append(row)
        return result


def build(puzzle: game.Puzzle):
    time_build_start = time.process_time()

    instance = Instance(puzzle, cpmpy.SolverLookup.get("ortools"))

    # let's try the representation where we store the index of each
    # extent.
    for rc, line in instance.puzzle.hints.items():
        for line_idx, hints in enumerate(line):
            for hint_idx, hint in enumerate(hints):
                instance.variables[rc, line_idx, hint_idx] = cpmpy.intvar(
                    0, instance.puzzle.size(rc), name=f"{rc.value}{line_idx}h{hint_idx}"
                )

    # extents can't run off the end of the row
    for rc, line in instance.puzzle.hints.items():
        for line_idx, hints in enumerate(line):
            for hint_idx, hint in enumerate(hints):
                hv = instance.variables[rc, line_idx, hint_idx]
                # if the hint is 2 and the length is 2, then the value
                # must be 0
                instance.model += hv <= instance.puzzle.size(rc) - hint

    # adjacent extents have to have a space between them
    for rc, line in instance.puzzle.hints.items():
        for line_idx, hints in enumerate(line):
            for (hint0_idx, hint0), (hint1_idx, hint1) in itertools.pairwise(
                enumerate(hints)
            ):
                h0v = instance.variables[rc, line_idx, hint0_idx]
                h1v = instance.variables[rc, line_idx, hint1_idx]
                # if h0 is 1 and h0v is 0, then h1v must be 2 or
                # greater. This indicates that this wants < rather
                # than <=.
                instance.model += h0v + hint0 < h1v

    # for all spaces in the grid, a row-hint fills that space == a
    # column-hint fills that space
    for row_idx, row_hints in enumerate(instance.puzzle.hints[game.Dim.ROW]):
        for col_idx, col_hints in enumerate(instance.puzzle.hints[game.Dim.COL]):
            row_variables = [
                instance.variables[game.Dim.ROW, row_idx, i]
                for i in range(len(row_hints))
            ]
            col_variables = [
                instance.variables[game.Dim.COL, col_idx, i]
                for i in range(len(col_hints))
            ]
            row_hint_covers = cpmpy.any(
                (rv + rh > col_idx) & (col_idx >= rv)
                for rv, rh in zip(row_variables, row_hints)
            )
            col_hint_covers = cpmpy.any(
                (cv + ch > row_idx) & (row_idx >= cv)
                for cv, ch in zip(col_variables, col_hints)
            )
            instance.model += (
                # if h0v is 0, then h0 of 1 covers column index 0. if
                # h0v is 0, then h0 of 2 covers column index 0 and 1.
                #
                # if h0v is 1, then h0 of 1 covers column index 1. if
                # h0v is 1, then h0 of 2 covers column index 1 and 2.
                row_hint_covers == col_hint_covers
            )

    time_build_end = time.process_time()
    instance.build_time = datetime.timedelta(seconds=time_build_end - time_build_start)

    return instance
