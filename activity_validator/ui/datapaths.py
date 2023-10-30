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
metrics_dir = "metrics"
diff_dir = "differences"


def check_paths():
    """
    Checks the specified paths for validation and input data
    """
    assert validation_path.is_dir(), f"Validation data not found: '{validation_path}'"
    assert input_data_path.is_dir(), f"Input data not found: '{input_data_path}'"
    subdirs = [prob_dir, freq_dir, duration_dir, metrics_dir, diff_dir]
    for subdir in subdirs[:3]:
        path = validation_path / subdir
        assert path.is_dir(), f"Validation data incomplete: {subdir} missing"
        assert len(
            list(path.glob("*.csv"))
        ), f"Validation subdirectory {subdir} is empty"
    for subdir in subdirs:
        path = input_data_path / subdir
        assert path.is_dir(), f"Input data incomplete: {subdir} missing"
        assert len(list(path.glob("*"))), f"Input subdirectory {subdir} is empty"


check_paths()
