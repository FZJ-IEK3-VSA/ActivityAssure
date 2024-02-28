"""
Example script for validation the LoadProfileGenerator
"""

import logging
from pathlib import Path

from activity_validator.lpgvalidation import validation
from activity_validator.hetus_data_processing.visualizations import metric_heatmaps
from activity_validator.hetus_data_processing import pandas_utils, utils
from activity_validator.lpgvalidation.validation_statistics import ValidationSet


@utils.timing
def validate_lpg():
    input_path = Path("data/lpg/preprocessed_single")
    custom_mapping_path = Path("examples/activity_mapping_lpg.json")
    person_trait_file = Path("data/lpg/person_characteristics.json")
    validation_data_path = Path(
        "data/validation data sets/country_sex_work status_day type"
    )

    output_path = Path("data/lpg/results")

    # load validation data statistics
    validation_statistics = ValidationSet.load(validation_data_path)

    # calculate or load input data statistics
    input_statistics = validation.process_model_data(
        input_path,
        custom_mapping_path,
        person_trait_file,
        validation_statistics.activities,
    )
    # input_statistics = ValidationSet.load(output_path)

    # if necessary, apply another mapping to merge activities
    validation_mapping_path = Path("examples/activity_mapping_validation_lpg.json")
    if validation_mapping_path is not None:
        mapping, _ = validation.load_mapping_and_activities(validation_mapping_path)
        input_statistics.map_statistics_activities(mapping)
        validation_statistics.map_statistics_activities(mapping)
        # define a new path to not overwrite the original validation data
        mapped_validation_path = Path(f"{validation_data_path}_mapped")
        validation_statistics.save(mapped_validation_path)

    input_statistics.save(output_path)

    # compare input and validation data statistics per profile type
    metrics_path = output_path / "metrics"
    metric_dict_variants = validation.validate_per_category(
        input_statistics, validation_statistics, output_path
    )
    for variant_name, metric_dict in metric_dict_variants.items():
        output_subdir = metrics_path / variant_name
        metrics_df = validation.metrics_dict_to_df(metric_dict)
        pandas_utils.save_df(
            metrics_df,
            "",
            f"metrics_per_category",
            base_path=output_subdir,
        )
        # validation.get_metric_means(metric_dict, output_subdir)
        plot_path = output_subdir / "heatmaps"
        metric_heatmaps.plot_indicators_by_profile_type(metrics_df, plot_path)
        metric_heatmaps.plot_indicators_by_activity(metrics_df, plot_path)
        metric_heatmaps.plot_profile_type_by_activity(metrics_df, plot_path)
    return

    # compare input and validation for each combination of profile types
    metrics_all_comb = validation.validate_all_combinations(
        input_statistics, validation_statistics
    )
    validation.save_file_per_metrics_per_combination(metrics_all_comb, output_path)
    metric_heatmaps.plot_category_comparison(metrics_all_comb, plot_path)
    metric_heatmaps.plot_category_comparison_per_activity(metrics_all_comb, plot_path)


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
    metric_heatmaps.plot_category_comparison(metrics, plot_path / "total")
    metric_heatmaps.plot_category_comparison_per_activity(
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
