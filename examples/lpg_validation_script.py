"""
Simple script for analyzing the KPIs from the LPG validation and identifying
the best and worst person categories.
"""

import pandas as pd
from pathlib import Path

result_path = Path("data/lpg/results/metrics/metrics_per_category.csv")

mean_idx = "mean"

data = pd.read_csv(result_path)

means = data[data.iloc[:, 1] == mean_idx]
means = means.sort_values(by="mae")
print(means)
