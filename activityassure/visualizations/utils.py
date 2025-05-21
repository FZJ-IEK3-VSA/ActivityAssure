CM_TO_INCH = 0.393701

LABEL_DICT = {
    "female": "♀",
    "male": "♂",
    "working day": "wd",
    "rest day": "rd",
    "unemployed": "ue",
    "full time": "ft",
    "part time": "pt",
    "student": "s",
    "retired": "r"
}

def replace_substrings(text, replacements):
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text