import dataclasses
import abc
import random
import collections

from nonogram import data


class Sampler(abc.ABC):
    @abc.abstractmethod
    def sample(self) -> data.InstanceConfig: ...

    @abc.abstractmethod
    def update(
        self, existing_data: dict[data.InstanceConfig, data.SolutionStatistics]
    ): ...


@dataclasses.dataclass
class UniformSampler(Sampler):
    config: data.SamplerConfig

    def sample(self) -> data.InstanceConfig:
        return random.choice(self.config.all_pts())

    def update(self, existing_data: dict[data.InstanceConfig, data.SolutionStatistics]):
        pass


@dataclasses.dataclass
class FillGapsSampler(Sampler):
    config: data.SamplerConfig
    existing: dict[data.InstanceConfig, data.SolutionStatistics]

    def sample(self) -> data.InstanceConfig:
        pts = self.config.all_pts()
        totals = collections.defaultdict(lambda: 0)
        for pt in self.config.all_pts():
            if pt in self.existing:
                totals[pt] = self.existing[pt].total
        random.shuffle(pts)
        pts.sort(key=lambda pt: totals[pt])
        return random.choices(pts, weights=range(len(pts)), k=1)[0]

    def update(self, existing_data: dict[data.InstanceConfig, data.SolutionStatistics]):
        self.existing_data = existing_data
