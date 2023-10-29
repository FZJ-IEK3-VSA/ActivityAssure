"""
Defines paths for the validation data set and the input data set to use
for validation.
"""

from pathlib import Path

# TODO: load paths from config file

# default data paths
validation_path = Path("data/validation_data EU")
input_data_path = Path("data/lpg/results")

# data subdirectories
prob_dir = "probability_profiles"
freq_dir = "activity_frequencies"
duration_dir = "activity_durations"
comp_dir = "comparison"
metrics_dir = "metrics"
diff_dir = "differences"
