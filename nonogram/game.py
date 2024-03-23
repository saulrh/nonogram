import dataclasses
import enum


@enum.unique
class Dim(enum.Enum):
    ROW = "r"
    COL = "c"


@dataclasses.dataclass
class Puzzle:
    hints: dict[Dim, list[list[int]]]

    def size(self, dim):
        if dim == Dim.ROW:
            return self.rows
        elif dim == Dim.COL:
            return self.cols

    @property
    def rows(self):
        return len(self.hints[Dim.COL])

    @property
    def cols(self):
        return len(self.hints[Dim.ROW])

