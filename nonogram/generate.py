import random
import more_itertools
import itertools
import dataclasses

from nonogram import game


@dataclasses.dataclass(frozen=True)
class Configuration:
    size: int
    prob: float

    def generate(self):
        cells = random.choices(
            [True, False], cum_weights=[self.prob, 1], k=self.size**2
        )
        grid = list(more_itertools.chunked(cells, self.size, strict=True))
        rows = []
        for row in range(self.size):
            row_hints = []
            for value, group in itertools.groupby(grid[row]):
                if value:
                    row_hints.append(len(list(group)))
            rows.append(row_hints)
        grid_t = list(more_itertools.transpose(grid))
        cols = []
        for col in range(self.size):
            col_hints = []
            for value, group in itertools.groupby(grid_t[col]):
                if value:
                    col_hints.append(len(list(group)))
            cols.append(col_hints)
        result = game.Puzzle({game.Dim.ROW: rows, game.Dim.COL: cols}, grid)
        return result


@dataclasses.dataclass
class SampleConfig:
    p_min: float
    p_max: float
    p_steps: int
    s_min: int
    s_max: int

    def _p_idx_to_p(self, p_idx: int) -> float:
        return self.p_min + p_idx * (self.p_max - self.p_min) / self.p_steps

    def all_sizes(self) -> list[int]:
        return list(range(self.s_min, self.s_max + 1, 1))

    def all_probs(self) -> list[float]:
        prob_idxs = range(self.p_steps)
        return [self._p_idx_to_p(p_idx) for p_idx in prob_idxs]

    def all_pts(self) -> list[Configuration]:
        sizes = self.all_sizes()
        probs = self.all_probs()
        return [
            Configuration(size=s, prob=p)
            for s, p in itertools.product(self.all_sizes(), self.all_probs())
        ]

    def uniform(self) -> Configuration:
        return random.choice(self.all_pts())

    # def weighted(
    #     self,
    #     data: dict[Configuration, float],
    # ) -> Configuration:
    #     pass

    def fill_gaps(
        self,
        data: dict[Configuration, float],
    ) -> Configuration:
        empty = []
        for pt in self.all_pts():
            if pt not in data:
                empty.append(pt)
        return random.choice(empty)
