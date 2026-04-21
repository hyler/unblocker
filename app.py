import argparse
from unblock import Unblock

parser = argparse.ArgumentParser(description='Solve sliding block puzzles.')
parser.add_argument(
    '-u',
    action='store_true',
    help='Treat all block as unique.'
)
parser.add_argument(
    'board_file',
    type=str,
    help='The file containing the board specification.'
)
args = parser.parse_args()

unblocker = Unblock(args.board_file)
unblocker.run()
