"""
Example of testing the validation framework with cross-validation
of the HETUS data.
"""

from activity_validator import utils, validation
from activity_validator.validation_statistics import ValidationSet
from activity_validator.visualizations import indicator_heatmaps


from pathlib import Path


@utils.timing
def cross_validation():
    output_path = Path("data/validation/cross_validation")

    # load the parts of the data
    data_path1 = Path("data/validation_data_sets/cross validation/validation split 1")
    data_path2 = Path("data/validation_data_sets/cross validation/validation split 2")
    data1 = ValidationSet.load(data_path1)
    data2 = ValidationSet.load(data_path2)

    # compare each category of data1 to each category of data2
    metrics = validation.validate_all_combinations(data1, data2)
    validation.save_file_per_indicator_per_combination(metrics, output_path)

    # plot a heatmap for each metric
    plot_path = output_path / "heatmaps"
    indicator_heatmaps.plot_category_comparison(metrics, plot_path / "total")
    indicator_heatmaps.plot_category_comparison_per_activity(
        metrics, plot_path / "per_activity"
    )


if __name__ == "__main__":
    cross_validation()
