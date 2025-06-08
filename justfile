solve_unique_demo:
	termshot --show-cmd --filename images/solve-2.png -- uv run solve_nonogram puzzles/2.xml

solve_nonunique_demo:
	termshot --show-cmd --filename images/solve-108.png -- uv run solve_nonogram puzzles/108.xml --max_solutions=10000

benchmark_csv_demo:
	termshot --show-cmd --filename images/benchmark_csv.png -- "uv run benchmark_nonogram --format=csv"

random_nonogram_demo:
	vhs demos/random_nonogram_demo.tape
	
benchmark_rich_demo:
	vhs demos/benchmark_rich_demo.tape

continue_demo: random_nonogram_demo
	vhs demos/continue_demo.tape

readme-assets: random_nonogram_demo benchmark_rich_demo solve_unique_demo solve_nonunique_demo benchmark_csv_demo continue_demo



lint:
	ruff check
	uv run pytype nonogram/ --keep-going
	uv run mypy nonogram/
