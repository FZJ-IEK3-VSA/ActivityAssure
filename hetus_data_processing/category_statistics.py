"""
Calculates statistics for each category of households, persons or diary entries.
These can then be used for validation.
"""

import logging
from typing import Any, Dict
import pandas as pd
import numpy as np

import hetus_columns as col
import hetus_translations


def calc_activity_group_frequencies(data: pd.DataFrame):
    pass
    # TODO: determine statistics to calculate
    # - mean and stddev/variance?
    # - maybe range?


def calc_probability_profiles(categories: Dict[Any, pd.DataFrame]) -> None:
    for cat, data in categories.items():
        # TODO when country is AT, there are only 96 timesteps
        # map to
        a1 = hetus_translations.aggregate_activities(data, 1)
        a1 = hetus_translations.extract_activity_names(a1)
        probabilities = a1.apply(lambda x: x.value_counts(normalize=True))
        probabilities.fillna(0.0, inplace=True)
        assert (
            np.isclose(probabilities.sum(), 1.0) | np.isclose(probabilities.sum(), 0.0)
        ).all(), "Calculation error: probabilities are not always 100 % (or 0 % for AT)"

        # save probability profiles to file
        path = f"./data/probability_profiles/probabilities {cat}.csv"
        probabilities.to_csv(path)
        logging.debug(f"Created probability profile file: {path}")
    logging.info(f"Created {len(categories)} probability profile files")

