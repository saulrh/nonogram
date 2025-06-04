import random
import more_itertools
import itertools

from nonogram import game


def random_puzzle(probability: float, size: int):
    cells = random.choices([True, False], cum_weights=[probability, 1], k=size**2)
    grid = list(more_itertools.chunked(cells, size, strict=True))
    rows = []
    for row in range(size):
        row_hints = []
        for value, group in itertools.groupby(grid[row]):
            if value:
                row_hints.append(len(list(group)))
        rows.append(row_hints)
    grid_t = list(more_itertools.transpose(grid))
    cols = []
    for col in range(size):
        col_hints = []
        for value, group in itertools.groupby(grid_t[col]):
            if value:
                col_hints.append(len(list(group)))
        cols.append(col_hints)
    result = game.Puzzle({game.Dim.ROW: rows, game.Dim.COL: cols}, grid)
    return result


def sample_config_uniform(
    p_min: float, p_max: float, p_steps: int, s_min: int, s_max: int
):
    s = random.randrange(s_min, s_max + 1)

    p_idx = random.randrange(p_steps)
    p = p_min + p_idx * (p_max - p_min) / p_steps

    return (s, p)
