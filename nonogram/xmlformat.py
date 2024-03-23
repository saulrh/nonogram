import bs4

from nonogram import game

def load(s):
    data = {}
    
    soup = bs4.BeautifulSoup(s, 'lxml-xml')

    for clue in soup.find_all('count'):
        if 'color' in clue.attrs:
            raise NotImplementedError('Puzzle has colors; solver does not support colors')

    for clues_node in soup.find_all('clues'):
        if clues_node.get('type') == "columns":
            dim = game.Dim.COL
        else:
            dim = game.Dim.ROW

        dim_data = []

        for line_idx, line_node in enumerate(clues_node.find_all('line')):
            line_data = []
            for clue_idx, clue_node in enumerate(line_node.children):
                line_data += [int(clue_node.text)]
            dim_data += [line_data]

        data[dim] = dim_data
    return game.Puzzle(data)
