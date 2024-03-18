"""
Simple script for analyzing the KPIs from the LPG validation and identifying
the best and worst person categories.
"""

import pandas as pd

from activity_validator.comparison_indicators import ValidationIndicators

# result_dir = "per_person"
result_dir = "default"
# result_dir = "default_first"

base_path = "data/lpg_validation/{}/validation_results/{}/indicators_per_category.csv"
mean_idx = ValidationIndicators.mean_column

data = pd.read_csv(base_path.format(result_dir, "default"))
data_scaled = pd.read_csv(base_path.format(result_dir, "scaled"))
# add the scaled indicators to the default dataframe
data_scaled = data_scaled.loc[:, ["mae", "rmse", "bias", "wasserstein"]].add_prefix(
    "scaled_"
)
data = pd.concat([data, data_scaled], axis=1)

# check various composite indicators
data["diff_mae"] = data["scaled_mae"] - data["mae"]
data["prod"] = data.loc[:, ["mae", "rmse", "wasserstein"]].product(axis=1) * 10**3
# print(data.describe())

# data.dropna(inplace=True)

data = data[data.iloc[:, 1] == mean_idx]
# filter category
# data = data[(data.iloc[:, 0].str.contains("unemployed_rest"))]

data = data.sort_values(by="prod")

print(data)
# print("\n--- Best")
# print(data[:20])
# print("\n--- Worst")
# print(data[-20:])
