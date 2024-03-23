nonogram solver in python based on CPMpy

# Usage

This project uses [poetry](https://python-poetry.org/). Invoke the
following to obtain dependencies:

```bash
poetry install
```

Find a puzzle on [Web Paint-By-Number](https://webpbn.com/). Grab the
ID of the puzzle off the end of the URL.

Run the following to fetch a copy of the puzzle to your local disk,
where the number at the end is the ID of the puzzle you grabbed in the
previous step:

```bash
poetry run get_nonogram 1
```

This will create an XML file in the `puzzles` directory.

Run the following to solve a nonogram:

```bash
poetry run solve_nonogram puzzles/1.xml
```

# Current limitations

Can only handle monochrome (black-and-white) puzzles, no color support
yet.

Can only accept puzzles in the XML format that webpbn xml format.

# Acknowledgments

Thanks to webpbn and its users for providing the problem instances in
the `puzzles/` directory. Having a set of instances whose designers
have given permission for redistribution makes this project a lot
easier.
