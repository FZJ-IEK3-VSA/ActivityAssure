"""Defines a ValidaitonIndicatorSet class for bundling indicators for all profile types."""

from dataclasses import dataclass

import pandas as pd

from activityassure.comparison_indicators import ValidationIndicators
from activityassure.profile_category import ProfileCategory


@dataclass
class ValidationIndicatorSet:
    """Stores the validation indicators for all profile categories."""

    indicators: dict[ProfileCategory, ValidationIndicators]
    #: the indicator variant stored (default, scaled, or normed)
    variant: str

    # TODO: indicator averages

    def indicator_dict_to_df(self) -> pd.DataFrame:
        """
        Convert the per-category indicator dict to a single dataframe
        containing all indicators, per activity and averages.

        :return: the indicator dataframe
        """
        dataframes = {pt: v.to_dataframe() for pt, v in self.indicators.items()}
        combined = pd.concat(dataframes.values(), keys=dataframes.keys())
        return combined
