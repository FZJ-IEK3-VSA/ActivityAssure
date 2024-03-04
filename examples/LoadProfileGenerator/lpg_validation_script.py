"""
Simple script for analyzing the KPIs from the LPG validation and identifying
the best and worst person categories.
"""

import pandas as pd

from activity_validator.comparison_indicators import ValidationIndicators

# TODO: turn this into a function to show a quick overview at the end of the validate_lpg() function?
#      E.g. overall best and worst categories/activities, worst according to each indicator etc.

result_dir = "per_person"
base_path = f"data/lpg_validation/{result_dir}/validation_results/default/indicators_per_category.csv"
mean_idx = ValidationIndicators.mean_column

data = pd.read_csv(base_path)
data_scaled = pd.read_csv(base_path.replace("default", "scaled"))
data_scaled = data_scaled.loc[:, ["mae", "rmse", "bias", "wasserstein"]].add_prefix(
    "scaled_"
)
data = pd.concat([data, data_scaled], axis=1)

data["diff_mae"] = data["scaled_mae"] - data["mae"]
data["prod"] = data.loc[:, ["mae", "rmse", "wasserstein"]].product(axis=1) * 10**3
print(data.describe())

# data.dropna(inplace=True)

data = data[data.iloc[:, 1] == mean_idx]
# filter category
# data = data[
#     (data.iloc[:, 0] == "DE_female_student_working day")
#     | (data.iloc[:, 0] == "DE_male_student_working day")
# ]
# filter activity

data = data.sort_values(by="prod")

print("--- Best")
print(data[:20])
print("\n--- Worst")
print(data[-20:])
