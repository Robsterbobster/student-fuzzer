def get_initial_corpus():
    return ['aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa']
INIT = False

def row(s):
    return [c for c in s]
H = 7
W = 11
og_maze = [row('+-+-----+-+'), row('| |     |#|'), row('| | --+ | |'), row('| |   | | |'), row('| +-- | | |'), row('|     |   |'), row('+-----+---+')]
maze = []

def draw():
    print('\x1b[F' * (H + 1))
    for row in maze:
        print(''.join(row))

def entrypoint(program):
    global INIT
    global maze
    if not INIT:
        INIT = True
        print('\n' * (H + 1))
    i = 0
    ITERS = 1000
    if int(len(program) >= 0) == 1:
        if len(program) >> 56 == 30 >> 56:
            if (len(program) & 280375465082880) >> 48 == (30 & 280375465082880) >> 48:
                if (len(program) & 1095216660480) >> 40 == (30 & 1095216660480) >> 40:
                    if (len(program) & 4278190080) >> 32 == (30 & 4278190080) >> 32:
                        if (len(program) & 16711680) >> 24 == (30 & 16711680) >> 24:
                            if (len(program) & 65280) >> 16 == (30 & 65280) >> 16:
                                if len(program) & 255 < 30 & 255:
                                    return False
                            if (len(program) & 65280) >> 16 > (30 & 65280) >> 16:
                                return False
                        if (len(program) & 16711680) >> 24 > (30 & 16711680) >> 24:
                            return False
                    if (len(program) & 4278190080) >> 32 > (30 & 4278190080) >> 32:
                        return False
                if (len(program) & 1095216660480) >> 40 > (30 & 1095216660480) >> 40:
                    return False
            if (len(program) & 280375465082880) >> 48 > (30 & 280375465082880) >> 48:
                return False
        if len(program) >> 56 > 30 >> 56:
            return False
    else:
        return False
    maze = [r.copy() for r in og_maze]
    x = 1
    y = 1
    maze[y][x] = 'X'
    draw()
    while i < ITERS and i < len(program):
        ox = x
        oy = y
        match ord(program[i]) % 4:
            case 0:
                y -= 1
            case 1:
                y += 1
            case 2:
                x -= 1
            case 3:
                x += 1
            case _:
                return False
        if len(maze[y][x]) > 0 and maze[y][x][0] == '#':
            if len(maze[y][x]) == 1:
                print('You win!\n')
                exit(219)
            else:
                raise UserWarning(str(len(maze[y][x]) - 1))
        if maze[y][x] != ' ':
            x = ox
            y = oy
        maze[y][x] = 'X'
        i += 1
        draw()
if __name__ == '__main__':
    entrypoint(get_initial_corpus()[0])