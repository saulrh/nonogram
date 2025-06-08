import dataclasses
import enum
from typing import Optional, Iterator
import rich.text
import rich.style

from nonogram import data


@enum.unique
class Dim(enum.Enum):
    ROW = "r"
    COL = "c"


@dataclasses.dataclass(frozen=True)
class Puzzle:
    config: data.InstanceConfig
    hints: dict[Dim, list[list[int]]]
    solution: Optional[list[list[bool]]] = None

    def size(self, dim):
        if dim == Dim.ROW:
            return self.n_cols
        elif dim == Dim.COL:
            return self.n_rows

    @property
    def n_cols(self):
        return len(self.hints[Dim.COL])

    @property
    def n_rows(self):
        return len(self.hints[Dim.ROW])

    def all_hints(self) -> Iterator[int]:
        for dim_hints in self.hints.values():
            for line_hints in dim_hints:
                yield from line_hints

    def max_hint_width(self) -> int:
        return max(len(str(h)) for h in self.all_hints())

    def to_text(
        self, with_hints: bool = True, with_solution: Optional[list[list[bool]]] = None
    ) -> rich.text.Text:
        cw = self.max_hint_width()

        hint_style = rich.style.Style(color="blue")
        grid_style = rich.style.Style(color="white", bold=True)
        cell_style = rich.style.Style(color="white")

        col_clue_height = max(len(col) for col in self.hints[Dim.COL])
        row_clue_width = max(len(row) for row in self.hints[Dim.ROW])

        if with_hints:
            frame_height = col_clue_height + 1
            frame_width = row_clue_width + 1
        else:
            frame_height = 0
            frame_width = 0

        row_text = [
            rich.text.Text(" " * cw, cell_style)
            for _ in range(frame_width + self.n_cols)
        ]
        chars = [list(row_text) for _ in range(frame_height + self.n_rows)]
        if with_hints:
            for col_idx, col_hints in enumerate(self.hints[Dim.COL]):
                for hint_idx, hint in enumerate(reversed(col_hints)):
                    row_num = col_clue_height - hint_idx - 1
                    char_num = frame_width + col_idx
                    chars[row_num][char_num] = rich.text.Text(
                        f"{hint:{cw}}", hint_style
                    )
                chars[col_clue_height][row_clue_width + col_idx + 1] = rich.text.Text(
                    "-" * cw, grid_style
                )
            for row_idx, row_hints in enumerate(self.hints[Dim.ROW]):
                for hint_idx, hint in enumerate(reversed(row_hints)):
                    row_num = frame_height + row_idx
                    char_num = row_clue_width - hint_idx - 1
                    chars[row_num][char_num] = rich.text.Text(
                        f"{hint:{cw}}", hint_style
                    )
                chars[col_clue_height + row_idx + 1][row_clue_width] = rich.text.Text(
                    "|" + " " * (cw - 1), grid_style
                )
            chars[col_clue_height][row_clue_width] = rich.text.Text(
                "+" + "-" * (cw - 1), grid_style
            )

        if with_solution:
            for row_idx, row in enumerate(with_solution):
                for col_idx, value in enumerate(row):
                    if value:
                        chars[row_idx + frame_height][col_idx + frame_width] = (
                            rich.text.Text("█" * cw, cell_style)
                        )

        return rich.text.Text("\n").join(rich.text.Text("").join(r) for r in chars)
