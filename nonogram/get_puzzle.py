import requests
import click
from rich import print
import pathlib
import time

from nonogram import xmlformat


@click.command
@click.argument("puzzle_ids", type=int, nargs=-1)
@click.option("-v", "--verbosity", type=int, default=1)
@click.option(
    "--puzzle_dir",
    type=click.Path(
        file_okay=False, dir_okay=True, writable=True, path_type=pathlib.Path
    ),
    default="puzzles",
)
@click.option(
    "--skip_existing/--no-skip-existing",
    type=bool,
    default=True,
)
@click.option(
    "--rate_limit_seconds",
    type=float,
    default=15,
)
def main(
    puzzle_ids: tuple[int, ...],
    verbosity: int,
    puzzle_dir: pathlib.Path,
    skip_existing: bool,
    rate_limit_seconds: float,
):
    def log(n, *args):
        if n <= verbosity:
            print(*args)

    puzzle_dir.mkdir(parents=True, exist_ok=True)

    for puzzle_id in puzzle_ids:
        puzzle_file = puzzle_dir / f"{puzzle_id}.xml"
        if puzzle_file.exists() and skip_existing:
            log(1, f"Already have puzzle {puzzle_id}, skipping")
            continue

        if len(puzzle_ids) > 1:
            time.sleep(rate_limit_seconds)

        try:
            r = requests.post(
                f"https://www.webpbn.com/export.cgi/webpbn{puzzle_id:06d}",
                data={
                    "fmt": "xml",
                    "go": puzzle_id,
                    "sid": "",
                    "id": puzzle_id,
                    "xml_clue": "on",
                    "xml_soln": "on",
                    "ss_soln": "on",
                    "sg_clue": "on",
                    "sg_soln": "on",
                },
            )
            if "DOCTYPE" not in r.text:
                log(1, r.text.strip())
                continue

            puzzle_file.write_text(r.text)

            log(1, f"Successfully got puzzle {puzzle_id}.")
            if verbosity > 1:
                puzzle = xmlformat.load(puzzle_file.read_text())
                log(2, f"Puzzle is {puzzle.n_cols} x {puzzle.n_rows}")
                if puzzle.solution is not None:
                    log(3, "Puzzle comes with solution: ")
                    log(3, puzzle.to_text(True, puzzle.solution))
        except Exception as e:
            print(e)


if __name__ == "__main__":
    main()
