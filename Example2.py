def get_initial_corpus():
    return ["aaaaaaaa"]

def entrypoint(s):
    if s == "I_am_bad":
        print("Found the bug!")
        exit(219)