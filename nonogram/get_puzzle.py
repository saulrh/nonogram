import requests
import click

@click.command
@click.argument("puzzle_id", type=int)
def main(puzzle_id):
    r = requests.post(
        f'https://www.webpbn.com/export.cgi/webpbn{puzzle_id:06d}',
        data={
            'fmt': 'xml',
            'go': puzzle_id,
            'sid': '',
            'id': puzzle_id,
            'xml_clue': 'on',
            'xml_soln': 'on',
            'ss_soln': 'on',
            'sg_clue': 'on',
            'sg_soln': 'on',
        },
    )
    with open(f'puzzles/{puzzle_id}.xml', 'wt') as f:
        f.write(r.text)


if __name__ == "__main__":
    main()
