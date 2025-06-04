import dataclasses
import enum
from typing import Optional


@enum.unique
class Dim(enum.Enum):
    ROW = "r"
    COL = "c"


@dataclasses.dataclass
class Puzzle:
    hints: dict[Dim, list[list[int]]]
    solution: Optional[list[list[bool]]] = dataclasses.field(default=None)

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

    def to_string(self):
        col_clue_height = max(len(col) for col in self.hints[Dim.COL])
        row_clue_width = max(len(row) for row in self.hints[Dim.ROW])
        row_text = [" " for _ in range(row_clue_width + self.cols + 1)]
        chars = [list(row_text) for _ in range(col_clue_height + self.rows + 1)]
        for col_idx, col_hints in enumerate(self.hints[Dim.COL]):
            for hint_idx, hint in enumerate(reversed(col_hints)):
                chars[col_clue_height - hint_idx - 1][row_clue_width + col_idx + 1] = (
                    str(hint)
                )
            chars[col_clue_height][row_clue_width + col_idx + 1] = "-"
        for row_idx, row_hints in enumerate(self.hints[Dim.ROW]):
            for hint_idx, hint in enumerate(reversed(row_hints)):
                chars[col_clue_height + row_idx + 1][row_clue_width - hint_idx - 1] = (
                    str(hint)
                )
            chars[col_clue_height + row_idx + 1][row_clue_width] = "|"
        chars[col_clue_height][row_clue_width] = "+"

        if self.solution:
            for row_idx, row in enumerate(solution):
                for col_idx, value in enumerate(row):
                    if value:
                        chars[row_idx + col_clue_height + 1][
                            col_idx + row_clue_width + 1
                        ] = "X"

        return "\n".join("".join(r) for r in chars)
