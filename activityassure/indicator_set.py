"""Defines a ValidaitonIndicatorSet class for bundling indicators for all profile types."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from activityassure import pandas_utils
from activityassure.comparison_indicators import ValidationIndicators
from activityassure.profile_category import ProfileCategory


@dataclass
class ValidationIndicatorSet:
    """Stores the validation indicators for all profile categories."""

    indicators: dict[ProfileCategory, ValidationIndicators]
    #: the indicator variant stored (default, scaled, or normed)
    variant: str

    def get_activity_indicators_averages(self) -> pd.DataFrame:
        """
        Calculate the indicator averages for each activity

        :return: dataframe with indicator averages
        """
        dflist = [indicators.to_dataframe() for indicators in self.indicators.values()]
        combined_df = pd.concat(dflist)
        activity_means = combined_df.groupby(combined_df.index).mean()
        return activity_means

    def indicator_dict_to_df(self) -> pd.DataFrame:
        """
        Convert the per-category indicator dict to a single dataframe
        containing all indicators, per activity and averages.

        :return: the indicator dataframe
        """
        dataframes = {pt: v.to_dataframe() for pt, v in self.indicators.items()}
        combined = pd.concat(dataframes.values(), keys=dataframes.keys())
        return combined

    def save(self, path: Path) -> pd.DataFrame:
        """
        Saves the indicator as a csv file to the given path.

        :param path: the path for the output file
        :return: the indicator dataframe that was saved
        """
        indicator_df = self.indicator_dict_to_df()
        pandas_utils.save_df(
            indicator_df,
            path.parent,
            path.name,
        )
        return indicator_df
