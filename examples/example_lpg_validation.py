"""
Example script for validation the LoadProfileGenerator
"""

import logging
from pathlib import Path

from activity_validator.lpgvalidation import validation
from activity_validator.hetus_data_processing.visualizations import metric_heatmaps
from activity_validator.hetus_data_processing import activity_profile, utils


@utils.timing
def process_model_data(
    input_path: Path,
    output_path: Path,
    custom_mapping_path: Path,
    person_trait_file: Path,
):
    """
    Processes the input data to produce the validation statistics.

    :param input_path: input data directory
    :param output_path: destination path for validation statistics
    :param custom_mapping_path: path of the activity mapping file
    :param person_trait_file: path of the person trait file
    """
    # load and preprocess all input data
    full_year_profiles = validation.load_activity_profiles_from_csv(
        input_path, person_trait_file
    )
    activity_mapping, activity_types = validation.load_mapping(
        custom_mapping_path, output_path
    )
    input_data_dict = validation.prepare_input_data(
        full_year_profiles, activity_mapping
    )
    validation.calc_category_sizes(input_data_dict, output_path)
    # calc and save input data statistics
    input_statistics = validation.calc_statistics_per_category(
        input_data_dict, output_path, activity_types
    )
    return input_statistics


@utils.timing
def validate_lpg():
    input_path = Path("data/lpg/preprocessed")
    output_path = Path("data/lpg/results_cluster")
    custom_mapping_path = Path("examples/activity_mapping_lpg.json")
    person_trait_file = Path("data/lpg/person_characteristics.json")

    # calculate or load input data statistics
    # input_statistics = process_model_data(
    #     input_path, output_path, custom_mapping_path, person_trait_file
    # )
    input_statistics = validation.load_validation_data(output_path)

    # load validation data statistics
    validation_data_path = Path("data/validation data sets/full_categorization")
    validation_statistics = validation.load_validation_data(validation_data_path)

    # compare input and validation data statistics per profile type
    metric_dict_variants = validation.validate_per_category(
        input_statistics, validation_statistics, output_path
    )
    for variant_name, metric_dict in metric_dict_variants.items():
        metrics_df = validation.metrics_dict_to_df(metric_dict)
        activity_profile.save_df(
            metrics_df,
            "metrics",
            f"metrics_per_category_{variant_name}",
            base_path=output_path,
        )
        metric_means = validation.get_metric_means(metric_dict, output_path)

    # compare input and validation for each combination of profile types
    metrics = validation.validate_all_combinations(
        input_statistics, validation_statistics
    )
    validation.save_file_per_metrics_per_combination(metrics, output_path)
    plot_path = output_path / "metrics" / "heatmaps"
    metric_heatmaps.plot_metrics_heatmaps(metrics, plot_path)
    metric_heatmaps.plot_metrics_heatmaps_per_activity(metrics, plot_path)


@utils.timing
def cross_validation():
    output_path = Path("data/lpg/results")

    # load the parts of the data
    data_path1 = Path("data/validation data sets/Validation Split 1")
    data1 = validation.load_validation_data(data_path1)
    data_path2 = Path("data/validation data sets/Validation Split 2")
    data2 = validation.load_validation_data(data_path2)

    # compare each category of data1 to each category of data2
    metrics = validation.validate_all_combinations(data1, data2)
    validation.save_file_per_metrics_per_combination(metrics, output_path)

    # plot a heatmap for each metric
    plot_path = output_path / "heatmaps"
    metric_heatmaps.plot_metrics_heatmaps(metrics, plot_path / "total")
    metric_heatmaps.plot_metrics_heatmaps_per_activity(
        metrics, plot_path / "per_activity"
    )


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # TODO: some general todos
    # - fix mypy issues
    # - standardize definition of file paths
    # - reevaluate all module-level constants: move to config file?
    # - check all the TODOs everywhere in the project

    validate_lpg()
