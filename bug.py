def get_initial_corpus():
    return ["aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"]

def entrypoint(s):
    if s == "I_really_want_to_stay_at_your_house":
        print("Found the bug!")
        exit(219)
