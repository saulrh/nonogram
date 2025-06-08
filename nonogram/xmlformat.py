import bs4
import bs4.element

from nonogram import game
from nonogram import data


def canonicalize_attr_value(av) -> str:
    if isinstance(av, list):
        return av[0]
    elif isinstance(av, str):
        return av
    raise RuntimeError("Not an attribute value list")


def load(s: str) -> game.Puzzle:
    hints = {}

    soup = bs4.BeautifulSoup(s, "lxml-xml")

    for clue in soup.find_all("count"):
        assert isinstance(clue, bs4.Tag), "Puzzle xml is malformed somehow"
        if "color" in clue.attrs:
            raise NotImplementedError(
                "Puzzle has colors; solver does not support colors"
            )

    for clues_node in soup.find_all("clues"):
        assert isinstance(clues_node, bs4.Tag), "Puzzle xml is malformed somehow"

        if clues_node.get("type") == "columns":
            dim = game.Dim.COL
        else:
            dim = game.Dim.ROW

        dim_data = []

        for line_idx, line_node in enumerate(clues_node.find_all("line")):
            line_data = []
            assert isinstance(line_node, bs4.Tag), "Puzzle xml is malformed somehow"
            for clue_idx, clue_node in enumerate(line_node.children):
                line_data += [int(clue_node.text)]
            dim_data += [line_data]

        hints[dim] = dim_data

    puzzle_node = soup.find("puzzle")
    assert puzzle_node is not None, f"puzzle {s} has no <puzzle> tag"
    assert isinstance(puzzle_node, bs4.Tag), "Puzzle xml is malformed somehow"
    default_color = canonicalize_attr_value(
        puzzle_node.attrs.get("defaultcolor", "black")
    )
    background_color = canonicalize_attr_value(
        puzzle_node.attrs.get("backgroundcolor", "white")
    )

    color_chars = {
        "black": "X",
        "white": ".",
    }
    for color_node in soup.find_all("color"):
        assert isinstance(color_node, bs4.Tag), "Puzzle xml is malformed somehow"
        color_name = canonicalize_attr_value(color_node.attrs["name"])
        color_chars[color_name] = canonicalize_attr_value(color_node.attrs["char"])

    grid = None
    for solution_node in soup.find_all("solution"):
        assert isinstance(solution_node, bs4.Tag), "Puzzle xml is malformed somehow"
        if "type" not in solution_node.attrs or solution_node.attrs["type"] == "goal":
            for image_node in solution_node.find_all("image"):
                grid = []
                for row_chars in image_node.text.splitlines():
                    grid_row = []
                    for char in row_chars:
                        if char == color_chars[background_color]:
                            cell_value = False
                        elif char == color_chars[default_color]:
                            cell_value = True
                        else:
                            continue
                        grid_row.append(cell_value)
                    if grid_row:
                        grid.append(grid_row)

    height = len(hints[game.Dim.ROW])
    width = len(hints[game.Dim.COL])
    size = (height + width) // 2
    if grid:
        prob = sum(sum(row) for row in grid) / (height * width)
    else:
        prob = 0
    instance_config = data.InstanceConfig(size=size, prob=prob)
    return game.Puzzle(config=instance_config, hints=hints, solution=grid)
