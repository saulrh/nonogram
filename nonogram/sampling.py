import dataclasses
import abc
import random
import collections

from nonogram import data


class Sampler(abc.ABC):
    @abc.abstractmethod
    def sample(self) -> data.InstanceConfig: ...

    @abc.abstractmethod
    def update(self, existing_data: dict[data.InstanceConfig, data.Solutions]): ...


@dataclasses.dataclass
class UniformSampler:
    config: data.SamplerConfig

    def sample(self) -> data.InstanceConfig:
        return random.choice(self.config.all_pts())

    def update(self, existing_data: dict[data.InstanceConfig, data.Solutions]):
        pass


@dataclasses.dataclass
class FillGapsSampler:
    config: data.SamplerConfig
    existing: dict[data.InstanceConfig, data.Solutions]

    def sample(self) -> data.InstanceConfig:
        pts = self.config.all_pts()
        biggest = max(s.total for s in self.existing.values())
        totals = collections.defaultdict(lambda: 0)
        for pt in self.config.all_pts():
            if pt in self.existing:
                totals[pt] = self.existing[pt].total
        random.shuffle(pts)
        pts.sort(key=lambda pt: totals[pt])
        return random.choices(pts, weights=range(len(pts)), k=1)[0]

    def update(self, existing_data: dict[data.InstanceConfig, data.Solutions]):
        self.existing_data = existing_data
