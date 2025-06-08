import os
import random
from rich import print
import rich.progress
import rich.table
import rich.text
import rich.live
import rich.layout
import rich.status
import rich.console
import click


from nonogram import xmlformat
from nonogram import solver

DEFAULT_MAX_SOLUTIONS = 1000


def lowpriority():
    os.nice(10)


@click.command
@click.argument("puzzle_file", type=click.File())
@click.option("--save_solutions_file", type=click.File(mode="w"))
@click.option("--max_solutions", type=int, default=DEFAULT_MAX_SOLUTIONS)
def solve_nonogram(puzzle_file, save_solutions_file, max_solutions: int):
    puzzle = xmlformat.load(puzzle_file.read())
    instance = solver.build(puzzle)
    print(f"Puzzle of size {puzzle.n_rows} x {puzzle.n_cols}, solving...")

    solutions = instance.solve_all(max_solutions)

    if len(solutions.grids) == 0:
        print("[bold red]No solutions found")
        exit(1)

    if len(solutions.grids) == 1:
        print("[green]Puzzle has a unique solution")
    elif len(solutions.grids) == max_solutions:
        print(f"[red]Puzzle has at least {max_solutions} solutions, stopping")
    else:
        print(f"[yellow]Found {len(solutions.grids)} solutions")

    if save_solutions_file:
        c = rich.console.Console(file=save_solutions_file)
        for grid in solutions.grids:
            c.print(puzzle.to_text(with_hints=False, with_solution=grid))
            c.print("\n")
            c.print("\n")

    if solutions.grids:
        solution_number, random_solution = random.choice(
            list(enumerate(solutions.grids))
        )
        if len(solutions.grids) > 1:
            print(f"Randomly selected solution {solution_number} to print:")
        print(puzzle.to_text(with_hints=True, with_solution=random_solution))
        print("")

    if puzzle.solution is not None:
        print("Puzzle's given solution:")
        print(puzzle.to_text(with_hints=True, with_solution=puzzle.solution))
        print("")
        for solution_no, solution in enumerate(solutions.grids):
            if solution == puzzle.solution:
                print("Solution", solution_no, rich.text.Text("MATCHES", "bold green"))
                break
        else:
            print(rich.text.Text("  No solution matches", "bold red"))

    print(f"Took {solutions.solve_all_time}")
