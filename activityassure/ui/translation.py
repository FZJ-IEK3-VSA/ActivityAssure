"""Defines classes and functions for translation in the ActivityAssure-UI"""

from enum import StrEnum
import json
from pathlib import Path

from activityassure.ui.config import config


class UIText(StrEnum):
    """Defines IDs for translatable strings in the ActivityAssure UI"""

    stacked_prob_curves = "stacked_prob_curves"
    activity_prob = "activity_prob"
    probability = "probability"
    prob_profiles = "prob_profiles"
    days = "days"
    overall = "overall"
    activities = "activities"
    prob_diff = "prob_diff"
    prob_curve_diff = "prob_curve_diff"
    prob_curves_norm = "prob_curves_norm"
    prob_curves_rel = "prob_curves_rel"
    prob_curves_abs = "prob_curves_abs"
    activity_freq = "activity_freq"
    activity_reps_per_day = "activity_reps_per_day"
    activity_duration = "activity_duration"
    activity_durations = "activity_durations"
    time = "time"
    mae_time = "mae_time"
    bias_time = "bias_time"
    rmse = "rmse"
    wasserstein_dist = "wasserstein_dist"
    pearson_corr = "pearson_corr"
    no_data_available = "no_data_available"


def load_translations(lang_code: str) -> dict[UIText, str]:
    """Loads a string translation dict for the specified language.

    :param lang_code: language code, e.g., EN
    :raises Exception: if no translations for the language are available
    :raises ValueError: if a value is missing in the translation dict
    :return: the translation dict
    """
    # load the translations file for the language
    lang_code = lang_code.lower()
    parent_dir = Path(__file__).parent
    file_path = parent_dir / f"languages/{lang_code}.json"
    if not file_path.is_file():
        raise Exception(f"Missing translations for language {lang_code}")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # check for missing keys
    missing_keys = [key.name for key in UIText if key.value not in data]
    if missing_keys:
        raise ValueError(f"Missing translations for keys: {missing_keys}")

    # return the translations dict
    return {UIText(key): value for key, value in data.items()}


#: global translation dict
LOADED_LANGUAGE_STRINGS = load_translations(config.language)


def get(id: UIText, *args) -> str:
    """Returns the matching str for the currently
    configured language.

    :param id: id the string to get
    :return: the matching string in the current language.
    """
    try:
        return LOADED_LANGUAGE_STRINGS[id].format(*args)
    except IndexError:
        raise Exception(f"Missing formatting arguments for UI text {id}: {args}")
