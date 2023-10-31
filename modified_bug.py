def entrypoint(s):
    x = 0
    if len(s) > 1:
        i1 = ord(s[0])
        i2 = ord(s[1])
        for i in range(0, i1 * i2):
            x += 1
    if len(s) > 2:
        if len(s[2]) > 0 and s[2][0] == 'b':
            if len(s[2]) == 1:
                if len(s) > 3 and s[3] == 'a':
                    if len(s) > 4 and s[4] == 'd':
                        if len(s) > 5 and s[5] == '!':
                            print(f'Found the bug after {x} loop iterations!')
                            exit(219)
            else:
                raise UserWarning(str(len(s[2]) - 1))