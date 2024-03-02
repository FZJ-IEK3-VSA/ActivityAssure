"""
Simple script for analyzing the KPIs from the LPG validation and identifying
the best and worst person categories.
"""

import pandas as pd

from activity_validator.comparison_indicators import ValidationIndicators

# TODO: turn this into a function to show a quick overview at the end of the validate_lpg() function?
#      E.g. overall best and worst categories/activities, worst according to each indicator etc.

base_path = (
    "data/lpg/results_tmp/validation_results/default/indicators_per_category.csv"
)
mean_idx = ValidationIndicators.mean_column

data = pd.read_csv(base_path)
data_scaled = pd.read_csv(base_path.replace("default", "scaled"))
data_scaled = data_scaled.loc[:, ("mae", "rmse", "bias", "wasserstein")].add_prefix("scaled_")  # type: ignore
data = pd.concat([data, data_scaled], axis=1)

data["diff_mae"] = data["scaled_mae"] - data["mae"]
data["prod"] = data.loc[:, ["mae", "rmse", "wasserstein"]].product(axis=1) * 10**6
print(data.describe())

# data.dropna(inplace=True)

data = data
# filter category
# data = data[
#     (data.iloc[:, 0] == "DE_female_student_working day")
#     | (data.iloc[:, 0] == "DE_male_student_working day")
# ]
# filter activity
data = data[data.iloc[:, 1] == mean_idx]

data = data.sort_values(by="prod")
print(data)
