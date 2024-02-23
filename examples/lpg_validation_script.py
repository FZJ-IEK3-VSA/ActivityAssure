"""
Simple script for analyzing the KPIs from the LPG validation and identifying
the best and worst person categories.
"""

import pandas as pd
from pathlib import Path

from activity_validator.lpgvalidation.comparison_metrics import ValidationMetrics

# TODO: turn this into a function to show a quick overview at the end of the validate_lpg() function?
#      E.g. overall best and worst categories/activities, worst according to each indicator etc.

base_path = "data/lpg/results/metrics/default/metrics_per_category.csv"
mean_idx = ValidationMetrics.mean_column

data = pd.read_csv(base_path)
data_scaled = pd.read_csv(base_path.replace("default", "scaled"))
data_scaled = data_scaled.loc[:, ("mae", "rmse", "bias", "wasserstein")].add_prefix("scaled_")  # type: ignore
data = pd.concat([data, data_scaled], axis=1)

data["diff_mae"] = data["scaled_mae"] - data["mae"]
print(data.describe())

# data.dropna(inplace=True)

data = data
# filter category
# data = data[data.iloc[:, 0] == "DE_female_retired_no work"]
# filter activity
data = data[data.iloc[:, 1] == mean_idx]

data = data.sort_values(by="mae")
print(data)
