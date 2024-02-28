"""
Defines paths for the validation data set and the input data set to use
for validation.
"""

from pathlib import Path

from activity_validator.lpgvalidation.validation_data import ValidationStatistics

# TODO: load paths from config file

# default data paths
validation_path = Path("data/validation data sets/de_mapped")
input_data_path = Path("data/lpg/results_tmp")

# data subdirectories
prob_dir = ValidationStatistics.PROBABILITY_PROFILE_DIR
freq_dir = ValidationStatistics.FREQUENCY_DIR
duration_dir = ValidationStatistics.DURATION_DIR
# metrics_dir = "metrics"
# diff_dir = "differences"

# directory for generated plots
output_path = Path("data/validation_plots")


def check_paths():
    """
    Checks the specified paths for validation and input data
    """
    assert validation_path.is_dir(), f"Validation data not found: '{validation_path}'"
    assert input_data_path.is_dir(), f"Input data not found: '{input_data_path}'"
    subdirs = [prob_dir, freq_dir, duration_dir]
    for subdir in subdirs:
        path = validation_path / subdir
        assert path.is_dir(), f"Validation data incomplete: {subdir} missing"
        assert len(
            list(path.glob("*.csv"))
        ), f"Validation subdirectory {subdir} contains no .csv files"
        path = input_data_path / subdir
        assert path.is_dir(), f"Input data incomplete: {subdir} missing"
        assert len(list(path.glob("*"))), f"Input subdirectory {subdir} is empty"


check_paths()
