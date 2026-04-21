import sys
import json
import math
import collections

class Segment:

    def __init__(self, row, col):
        self.row = row
        self.col = col


class Unblock:

    def __init__(self, board_file):

        with open(board_file, 'rt') as f:
            board_config = json.load(f)

        self.validate_board_config(board_config)

        self.board_config = board_config
        self.rows = self.board_config.get('rows')  # Original board setup.
        self.exits = self.board_config.get('exits')
        self.movements = self.board_config.get('movements')

        # For an m x n puzzle we need an (m + 2) x (n + 2) board, because we
        # have borders all around. This program works with these larger
        # dimensions for all purposes.
        self.height = len(self.board_config.get('rows')) + 2
        self.width = len(self.board_config.get('rows')[0]) + 2


    def run(self):

        # For the initial board, board_from_pieces() will use data directly
        # from self.rows to create the board. A boardpack is a dictionary
        # containing the board and its attributes. Currently those are the
        # parent board (as an encoded board string) and the piece whose move
        # produced the current board from the parent.
        starting_boardpack = {
            'board': self.board_from_pieces(pieces=None),
            'attrs': {
                'parent': None,
                'piece': None
            }
        }
        starting_moveset = self.generate_moves(starting_boardpack)

        ### NEW DEV
        # pieces = self.pieces_from_board(starting_boardpack.get('board'))
        # self.unify_pieces(pieces)
        # sys.exit(0)
        ### NEW DEV END

        # The starting board has no parent and no piece move produced it. The
        # starting unseen boards are the first boards reachable immediately
        # from the initial board; there may be none of those.
        #
        # The seen boards are a dict keyed on the board string, so that we can
        # easily check whether a board is in or not, and trace lineage.
        seen_boards = {
            starting_boardpack.get('board'): starting_boardpack.get('attrs')
        }
        unseen_boards = collections.OrderedDict()

        # generate_boards() returns a list of boardpacks.
        for boardpack in self.generate_boards(starting_moveset):
            unseen_boards.update({
                boardpack.get('board'): boardpack.get('attrs')
            })

        solved_boards = collections.OrderedDict()
        shortest_path = None

        # Let's rewrite this using "while True:" and then refactoring it back
        # once the logic is proven to be correct.
        #
        # Let's make sure we're not double-inserting boards.
        # Let's document the move and board generation pieces.
        # Let's review how moveset and boardset generation works.
        # Let's make the above ones in order, if possible, for repeatability.
        # Document the pretty print function, especially the code lookup.
        # Unify and improve the initial board generation, is there a need
        #   for a function to really either take pieces or not? Seems silly.
        # Need to determine what board attributes are really needed and if they
        #   help, otherwise it's complicating things for no good reason.
        # Basically, we need to take a deeper look at EVERYTHING.

        # AND MAKE SURE TO DOCUMENT THE BOARD FORMATS! Sometimes it's dicts,
        # other times it's lists, encoding, decoding, it makes things unclear.
        # Either rewrite it and make it consistent, or DOCUMENT IT BETTER!

        while True:

            if not unseen_boards:
                break

            # Pop an unseen board off the dict.
            board, attrs = unseen_boards.popitem(last=False)

            # If the board has been seen, don't even process it.
            if board in seen_boards:
                continue

            # First, add the board to the seen boards.
            seen_boards.update({board: attrs})

            # How far we are from the starting board.
            distance = self.path_length(board, seen_boards)

            # Board is a solution, so it's a terminal board. If it's closer
            # than the current shortest path, update the shortest path.
            if self.is_solved(board):
                solved_boards.update({board: distance})
                if not shortest_path or distance < shortest_path:
                    shortest_path = distance
                continue

            # Board is not a solution, but it's further than the shortest path
            # we've seen so far, so it's a dead end. Don't generate from it.
            if shortest_path and distance >= shortest_path:
                continue

            # Board is neither terminal nor a dead end, so we can try to
            # generate some moves from it.
            moveset = self.generate_moves({
                'board': board,
                'attrs': attrs
            })
            boardset = self.generate_boards(moveset)

            # If a candidate has been seen already, skip it.
            for candidate in boardset:
                candidate_board = candidate.get('board')
                candidate_attrs = candidate.get('attrs')

                if (
                    not candidate_board in seen_boards
                    and not candidate_board in unseen_boards
                ):
                    unseen_boards.update({candidate_board: candidate_attrs})

        print(f'Total boards found: {len(seen_boards)}')

        # We've generated all the possible boards for this game (or we've
        # crashed due to OOM.) Let's look for solutions and trace them back to
        # the initial board.
        if solved_boards:
            print(f'Solution boards found: {len(solved_boards)}')
        else:
            print('No solutions found.')
            return

        solutions = dict()

        for board, distance in solved_boards.items():
            if distance not in solutions:
                solutions.update({distance: list()})
            solutions.get(distance).append(board)

        ## CUSTOM
        bb = solutions.get(min(solutions))[0]
        parent = seen_boards.get(bb).get('parent')
        piece = seen_boards.get(bb).get('piece')
        self.pretty_print_board(bb, piece=piece, id=True)
        while parent:
            if parent:
                piece = seen_boards.get(parent).get('piece')
                self.pretty_print_board(parent, piece=piece, id=True)
            else:
                piece = None
            parent = seen_boards.get(parent).get('parent')
        ## /CUSTOM


    def validate_board_config(self, board_config):

        # TODO: Need to make sure these sections exists first.

        rows = board_config.get('rows')
        exits = board_config.get('exits')
        movements = board_config.get('movements')

        # Make sure all rows are the same length.
        row_lengths = [len(row) for row in rows]
        if len(set(row_lengths)) != 1:
            raise Exception('All rows must be the same length.')


    def unify_pieces(self, pieces):

        # Attempt to determine which pieces are equivalent. The criteria are:
        #
        #   * Any pieces that have the same shape, and
        #   * Can move in the same directions
        #
        # Unified pieces are considered "the same piece" for movement and board
        # coverage purposes. For example, if pieces "a" and "b" both consist of
        # two horizontal segments ([a][a] and [b][b]) and they can both move
        # horizontally and vertically, then in any board position they can be
        # "swapped" with each other without changing the board.
        #
        # This allows us to "collapse" many unique boards into one, because
        # distinguishing all pieces is probably not important for the solution.

        for piece, segments in pieces.items():
            print(f'Piece: {piece}')
            for segment in segments:
                print(f'  ({segment.row}, {segment.col})')


    def is_solved(self, board):

        # For each segment in the prisoner piece (denoted by * here), check if
        # there's a clear path to the outside.
        #
        # Start with the assumption that the piece is free to escape on each
        # side, with each of its segments. At the first encountered obstacle,
        # disqualify the respective direction.

        # BETTER IDEA (Maybe?)
        #
        # Get the min and max coordinates for the prisoner piece, in both
        # dimensions. Then, check if there's an opening spanning these
        # coordinates. If there is, in theory this should mean that the
        # piece would be able to "fit" through such an opening, on whatever
        # side it is.

        pieces = self.pieces_from_board(board)
        board = self.decode_board(board)
        exit_up = exit_right = exit_down = exit_left = True

        for seg in pieces.get('*'):

            row = seg.row
            col = seg.col

            # Check for escape route going up.
            for r in range(row, -1, -1):
                if (
                    board[r][col] != '*'
                    and (board[r][col] != ' '
                    and board[r][col] != '@')
                ):
                    exit_up = False

            # Check for escape route going right.
            for c in range(col, self.width):
                if (
                    board[row][c] != '*'
                    and board[row][c] != ' '
                    and board[row][c] != '@'
                ):
                    exit_right = False

            # Check for escape route going down.
            for r in range(row, self.height):
                if (
                    board[r][col] != '*'
                    and board[r][col] != ' '
                    and board[r][col] != '@'
                ):
                    exit_down = False

            # Check for escape route going left.
            for c in range(col, -1, -1):
                if (
                    board[row][c] != '*'
                    and board[row][c] != ' '
                    and board[row][c] != '@'
                ):
                    exit_left = False

        if exit_up or exit_right or exit_down or exit_left:
            return True

        return False


    def path_length(self, board, boardset):

        path_length = 0
        parent = boardset.get(board).get('parent')

        while parent:
            parent = boardset.get(parent).get('parent')
            path_length += 1

        return path_length


    def get_coverage(self, board):
        '''Unused.'''

        pieces = self.pieces_from_board(board)
        board = self.decode_board(board)

        groups = list()

        for piece, segments in pieces.items():
            group = list()
            for segment in segments:
                group.append(str(segment.row) + str(segment.col))
            groups.append(''.join(sorted(group)))

        coverage = ''.join(sorted(groups))

        return coverage


    def board_from_pieces(self, pieces=None):

        # A board in this app is represented by a string, which is the
        # concatenation of the rows that make up the board. There is a border
        # all around, denoted by #, and exits are denoted by @. An example
        # board may look like this:
        #
        # #######a**b##a**b##cdde##cfge##h  i###@@##
        #
        # The rectangular representation of this board is:
        #
        #   Without borders:              With borders:
        #
        #                                     ######
        #         a**b                        #a**b#
        #         a**b                        #a**b#
        #         cdde                        #cdde#
        #         cfge                        #cfge#
        #         h  i                        #h  i#
        #                                     ##@@##

        # The rectangular representation is stored in a list, where each list
        # element is a row from the board. Converting from the rectangular
        # format (list) to the compact one (string) is done by the
        # encode_board() method, and conversely by the decode_board() method.

        # Any other method in this program expects to receive an ENCODED board,
        # and if it needs to do anything with it, it needs to decode it first.

        # If pieces are given, then use the information from there to assign
        # the characters that make up the board. Otherwise (such as during the
        # very first build), use the characters from self.rows that were read
        # in from the input file.

        board = list()

        # r = row, c = col
        for r in range(self.height):
            board.append(list())
            for c in range(self.width):
                if r == 0:
                # We're in the topmost row, which is a border row.
                    if c in self.exits.get('top'):
                        board[r].append('@')
                    else:
                        board[r].append('#')
                elif r == self.height-1:
                # We're in the bottommost row, which is a border row.
                    if c in self.exits.get('bottom'):
                        board[r].append('@')
                    else:
                        board[r].append('#')
                elif c == 0:
                # We're in the leftmost column, which is a border column.
                    if r in self.exits.get('left'):
                        board[r].append('@')
                    else:
                        board[r].append('#')
                elif c == self.width-1:
                # We're in the rightmost column, which is a border column.
                    if r in self.exits.get('right'):
                        board[r].append('@')
                    else:
                        board[r].append('#')
                else:
                # We're not anywhere on the border, so assign the piece chars.
                    if pieces:
                    # Create the board as blank since piece characters will be
                    # assigned later.
                        board[r].append(' ')
                    else:
                    # No pieces given, use self.rows for the characters.
                        board[r].append(self.rows[r-1][c-1])  # Initial build.

        if pieces:
            for piece, segments in pieces.items():
                for segment in segments:
                    board[segment.row][segment.col] = piece

        return self.encode_board(board)


    def pieces_from_board(self, board):

        # The pieces making up the board and their constituent segments. This
        # is not a complete representation since the borders and exit(s) are
        # not included.
        #
        # The data structure is a dictionary with the keys the characters that
        # represent the pieces ('a', 'b', etc.) and the values a list of the
        # Segment objects that make up each piece. The Segment objects hold the
        # coordinates of the segments making up the piece.
        #
        # {
        #     'a': [
        #         <unblock.Segment object at 0x103f57820>,
        #         <unblock.Segment object at 0x103f716a0>
        #     ],
        #     '*': [
        #         <unblock.Segment object at 0x103f71ee0>,
        #         <unblock.Segment object at 0x103f71370>,
        #         ...
        #     ],
        #     ...,
        #     'h': [<unblock.Segment object at 0x103f3c310>],
        #     'i': [<unblock.Segment object at 0x103f3c130>]
        # }

        board = self.decode_board(board)
        pieces = collections.OrderedDict()

        # r is the row, c is the column
        for r in range(1, self.height-1):
            for c in range(1, self.width-1):
                char = board[r][c]
                if char == ' ':
                    continue
                if char not in pieces:
                    pieces.update({char: list()})
                pieces.get(char).append(Segment(r, c))

        return pieces


    def generate_moves(self, boardpack):

        # 'moves': {
        #   'a': {
        #     'u': 2,
        #     'd': 1
        #   },
        #   'c': {
        #     'r': 1
        #   }
        # }

        # It is this function that handles whether a piece moves horizontally
        # or vertically.

        board = boardpack.get('board')  # Still encoded at this point.
        pieces = self.pieces_from_board(board)
        board = self.decode_board(board)

        moveset = None
        moves = collections.OrderedDict()

        for piece, segments in pieces.items():

            for direction in {'u', 'r', 'd', 'l'}:

                # If we're considering moving horizontally or vertically and
                # the piece is not allowed to move that way, skip generation.
                if (
                    direction in {'u', 'd'}
                    and not piece in self.movements.get('vertical')
                ) or (
                    direction in {'r', 'l'}
                    and not piece in self.movements.get('horizontal')
                ):
                    continue

                segment_maximums = list()

                for segment in segments:
                    row = segment.row
                    col = segment.col
                    segment_max_move = 0

                    if direction == 'u':
                        while (
                            row > 1 and (
                                board[row-1][col] == piece
                                or board[row-1][col] == ' '
                            )
                        ):
                            segment_max_move += 1
                            row -= 1

                    if direction == 'r':
                        while (
                            col < self.width-1 and (
                                board[row][col+1] == piece
                                or board[row][col+1] == ' '
                            )
                        ):
                            segment_max_move += 1
                            col += 1

                    if direction == 'd':
                        while (
                            row < self.height-1 and (
                                board[row+1][col] == piece
                                or board[row+1][col] == ' '
                            )
                        ):
                            segment_max_move += 1
                            row += 1

                    if direction == 'l':
                        while (
                            col > 1 and (
                                board[row][col-1] == piece
                                or board[row][col-1] == ' '
                            )
                        ):
                            segment_max_move += 1
                            col -= 1

                    segment_maximums.append(segment_max_move)

                if min(segment_maximums) > 0:
                    if piece not in moves:
                        moves.update({piece: dict()})
                    moves.get(piece).update({direction: min(segment_maximums)})

        moveset = dict({
            'board': self.encode_board(board),
            'moves': moves
        })

        return moveset


    def generate_boards(self, moveset, cull=False):

        board = moveset.get('board')
        moves = moveset.get('moves')
        boards = list()
        culled = 0

        for piece, movelist in moves.items():

            for direction, distance in movelist.items():
                pieces = self.pieces_from_board(board)

                for _ in range(distance):
                    for segment in pieces.get(piece):
                        if direction == 'u':
                            segment.row -= 1
                        if direction == 'r':
                            segment.col += 1
                        if direction == 'd':
                            segment.row += 1
                        if direction == 'l':
                            segment.col -= 1

                    if cull:
                        brd = self.board_from_pieces(pieces)
                        if brd in self.seen_boards:
                            print(f'Culling {brd} (parent: {board}')
                            culled += 1
                            continue
                    boards.append({
                        'board': self.board_from_pieces(pieces),
                        'attrs': {
                            'parent': board,
                            'piece': piece
                        }
                    })

        return boards


    def encode_board(self, board):
        return ''.join([str(item) for row in board for item in row])


    def decode_board(self, string):
        return [
            [i for i in string[j:j+self.width]]
            for j in range(0, len(string), self.width)
        ]


    def print_board(self, board):

        if isinstance(board, str):
            board = self.decode_board(board)

        for row in board:
            print(''.join(row))


    def print_pieces(self, pieces):

        for char, segments in pieces.items():
            print(f'{char}:')
            for segment in segments:
                print(f'  ({segment.row}, {segment.col})')


    def pretty_print_board(self, board, piece=None, id=False):

        # piece is the character of the piece that moved last, so we can shade
        # it a little differently for visibility.

        board = self.decode_board(board)

        BORDERS = {
            '0000': ' ',
            '0001': '╝',
            '0010': '╗',
            '0011': '║',
            '0100': '╔',
            '0110': '═',
            '0111': '╚',
            '0012': '╣',
            '0120': '╦',
            '0122': '╠',
            '0112': '╩',
            '0123': '╬',
            '0121': '╬',
            '0101': '╬'
        }

        h = self.height
        w = self.width

        height = ((self.height - 2) * 2) + 1
        width = ((self.width - 2) * 4) + 1

        pp_board = list()

        for r in range(height):
            pp_board.append(list())
            for c in range(width):

                if r == 0:
                    if c == 0:
                        pp_board[r].append('╔')
                    elif c == width-1:
                        pp_board[r].append('╗')
                    else:
                        if c % 4 == 0:
                            col = c // 4
                            if board[1][col] == board[1][col+1]:
                                pp_board[r].append('═')
                            else:
                                pp_board[r].append('╦')
                        else:
                            pp_board[r].append('═')
                elif r == height-1:
                    if c == 0:
                        pp_board[r].append('╚')
                    elif c == width-1:
                        pp_board[r].append('╝')
                    else:
                        if c % 4 == 0:
                            col = c // 4
                            if board[h-2][col] == board[h-2][col+1]:
                                pp_board[r].append('═')
                            else:
                                pp_board[r].append('╩')
                        else:
                            pp_board[r].append('═')
                elif r % 2 == 1:
                    if c == 0 or c == width-1:
                        pp_board[r].append('║')
                    else:
                        if c % 4 == 0:
                            row = (r + 1) // 2
                            col = c // 4
                            if board[row][col] == board[row][col+1]:
                                if board[row][col] != ' ':
                                    if board[row][col] == piece:
                                        if id:
                                            pp_board[r].append(board[row][col+1].upper())
                                        else:
                                            pp_board[r].append('▒')
                                    elif board[row][col] == '*':
                                        pp_board[r].append('█')
                                    else:
                                        if id:
                                            pp_board[r].append(board[row][col+1])
                                        else:
                                            pp_board[r].append('░')
                                else:
                                    pp_board[r].append(' ')
                            else:
                                pp_board[r].append('║')
                        else:
                            row = (r + 1) // 2
                            col = math.ceil(c/4)
                            if board[row][col] != ' ':
                                if board[row][col] == piece:
                                    if id:
                                        pp_board[r].append(board[row][col].upper())
                                    else:
                                        pp_board[r].append('▒')
                                elif board[row][col] == '*':
                                    pp_board[r].append('█')
                                else:
                                    if id:
                                        pp_board[r].append(board[row][col])
                                    else:
                                        pp_board[r].append('░')
                            else:
                                pp_board[r].append(' ')
                else:
                    if c == 0:
                        if board[r//2][1] == board[r//2+1][1]:
                            pp_board[r].append('║')
                        else:
                            pp_board[r].append('╠')
                    elif c == width-1:
                        if board[r//2][w-2] == board[r//2+1][w-2]:
                            pp_board[r].append('║')
                        else:
                            pp_board[r].append('╣')
                    else:
                        if c % 4 == 0:
                            row = r // 2
                            col = c // 4

                            tr = 0
                            if board[row+1][col+1] == board[row][col+1]:
                                br = tr
                            else:
                                br = tr + 1

                            if board[row+1][col] == board[row][col+1]:
                                bl = tr
                            elif board[row+1][col] == board[row+1][col+1]:
                                bl = br
                            else:
                                bl = br + 1

                            if board[row][col] == board[row][col+1]:
                                tl = tr
                            elif board[row][col] == board[row+1][col+1]:
                                tl = br
                            elif board[row][col] == board[row+1][col]:
                                tl = bl
                            else:
                                tl = bl + 1

                            code = [str(seg) for seg in [tr, br, bl, tl]]
                            code = ''.join(code)
                            pp_board[r].append(BORDERS.get(code))
                        else:
                            col = math.ceil(c/4)
                            if board[r//2][col] == board[r//2+1][col]:
                                if board[r//2][col] != ' ':
                                    if board[(r+1)//2][col] == piece:
                                        if id:
                                            pp_board[r].append(board[r//2][col].upper())
                                        else:
                                            pp_board[r].append('▒')
                                    elif board[(r+1)//2][col] == '*':
                                        pp_board[r].append('█')
                                    else:
                                        if id:
                                            pp_board[r].append(board[r//2][col])
                                        else:
                                            pp_board[r].append('░')
                                else:
                                    pp_board[r].append(' ')
                            else:
                                pp_board[r].append('═')

        self.print_board(pp_board)
