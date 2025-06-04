CM_TO_INCH = 0.393701

LABEL_DICT = {
    "female": "♀",
    "male": "♂",
    "working day": "wd",
    "rest day": "rd",
    "undetermined": "",
    "unemployed": "ue",
    "full time": "ft",
    "part time": "pt",
    "student": "s",
    "retired": "r",
}

ERROR_METRIC_DICT = {
    "mae": "MAE",
    "bias": "Bias",
    "rmse": "RMSE",
    "wasserstein": "Wasserstein",
    "pearson_corr": "PCC",
}


def replace_substrings(text: str, replacements: dict) -> str:
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text
