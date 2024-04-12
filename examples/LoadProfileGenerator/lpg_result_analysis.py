"""
Simple script for analyzing the KPIs from the LPG validation and identifying
the best and worst person categories.
"""

import pandas as pd

from activity_validator.comparison_indicators import ValidationIndicators

if __name__ == "__main__":
    # path template for the indicator file for different indicator variants
    base_path = (
        "data/validation/lpg_example/validation_results/{}/indicators_per_category.csv"
    )
    mean_idx = ValidationIndicators.mean_column

    # load the indicators
    indicators_default = pd.read_csv(base_path.format("default"))
    indicators_scaled = pd.read_csv(base_path.format("scaled"))
    # add the scaled indicators to the default dataframe
    indicators_scaled = indicators_scaled.loc[
        :, ["mae", "rmse", "bias", "wasserstein"]
    ].add_prefix("scaled_")
    indicators_default = pd.concat([indicators_default, indicators_scaled], axis=1)

    # calculate the product of the indicators as a new composite indicator
    indicators_default["product"] = (
        indicators_default.loc[:, ["mae", "rmse", "wasserstein"]].product(axis=1)
        * 10**3
    )

    # only select the mean indicators, exclude per-activity indicators
    indicators_default = indicators_default[indicators_default.iloc[:, 1] == mean_idx]

    # filter by category
    # data = data[(data.iloc[:, 0].str.contains("unemployed_rest"))]

    # choose an indicator to sort by
    indicators_default = indicators_default.sort_values(by="product")

    print(indicators_default)
