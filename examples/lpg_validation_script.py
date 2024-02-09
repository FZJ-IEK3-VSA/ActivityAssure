"""
Simple script for analyzing the KPIs from the LPG validation and identifying
the best and worst person categories.
"""

import pandas as pd
from pathlib import Path

base_path = "data/lpg/results_cluster/metrics/metrics_per_category_"
mean_idx = "mean"

data = pd.read_csv(base_path + "default.csv")
data_scaled = pd.read_csv(base_path + "scaled.csv")
data_scaled = data_scaled.loc[:, ("mae", "rmse", "wasserstein")].add_prefix("scaled_")  # type: ignore
data = pd.concat([data, data_scaled], axis=1)

data["diff"] = data["scaled_mae"] - data["mae"]
data.dropna(inplace=True)
print(data.describe())

filtered = data
# filter category
# filtered = data[data.iloc[:, 0] == "DE_female_full time_work"]
# filter activity
# filtered = data[data.iloc[:, 1] == mean_idx]

filtered = filtered.sort_values(by="bias")
print(filtered)
