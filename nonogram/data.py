import dataclasses
import datetime
import itertools
from typing import Optional


@dataclasses.dataclass
class SolutionStatistics:
    unique: int
    total: int
    runtime: datetime.timedelta

    def ratio(self) -> float:
        return float(self.unique) / float(self.total)

    def average_runtime(self) -> datetime.timedelta:
        return self.runtime / self.total


@dataclasses.dataclass(frozen=True)
class InstanceConfig:
    size: int
    prob: float


@dataclasses.dataclass(frozen=True)
class SamplerConfig:
    p_min: float
    p_max: float
    p_steps: int
    s_min: int
    s_max: int

    def p_idx_to_p(self, p_idx: int) -> float:
        return self.p_min + p_idx * (self.p_max - self.p_min) / self.p_steps

    def all_sizes(self) -> list[int]:
        return list(range(self.s_min, self.s_max + 1, 1))

    def all_probs(self) -> list[float]:
        prob_idxs = range(self.p_steps)
        return [self.p_idx_to_p(p_idx) for p_idx in prob_idxs]

    def all_pts(self) -> list[InstanceConfig]:
        return [
            InstanceConfig(size=s, prob=p)
            for s, p in itertools.product(self.all_sizes(), self.all_probs())
        ]


@dataclasses.dataclass(frozen=True)
class Solution:
    is_unique: bool
    solve_time: datetime.timedelta
    config: InstanceConfig
    grid: Optional[list[list[bool]]] = None


@dataclasses.dataclass(frozen=True)
class Solutions:
    solve_all_time: datetime.timedelta
    grids: list[list[list[bool]]]
