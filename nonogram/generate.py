import random
import more_itertools
import itertools

from nonogram import game
from nonogram import data


def generate(config: data.InstanceConfig) -> game.Puzzle:
    cells = random.choices(
        [True, False], cum_weights=[config.prob, 1], k=config.size**2
    )
    grid = list(more_itertools.chunked(cells, config.size, strict=True))
    rows = []
    for row in range(config.size):
        row_hints = []
        for value, group in itertools.groupby(grid[row]):
            if value:
                row_hints.append(len(list(group)))
        rows.append(row_hints)
    grid_t = list(more_itertools.transpose(grid))
    cols = []
    for col in range(config.size):
        col_hints = []
        for value, group in itertools.groupby(grid_t[col]):
            if value:
                col_hints.append(len(list(group)))
        cols.append(col_hints)
    result = game.Puzzle({game.Dim.ROW: rows, game.Dim.COL: cols}, grid)
    return result
