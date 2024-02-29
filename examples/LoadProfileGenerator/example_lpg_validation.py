"""
Example script for validation the LoadProfileGenerator
"""

import logging
from pathlib import Path

from activity_validator import utils, pandas_utils
from activity_validator import validation
import activity_validator.input_data_processing.process_model_data
from activity_validator.visualizations import indicator_heatmaps
from activity_validator.validation_statistics import ValidationSet


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
    input_statistics = (
        activity_validator.input_data_processing.process_model_data.process_model_data(
            input_path,
            custom_mapping_path,
            person_trait_file,
            validation_statistics.activities,
        )
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
    validation_result_path = output_path / "validation_results"
    indicator_dict_variants = validation.validate_per_category(
        input_statistics, validation_statistics, output_path
    )
    for variant_name, metric_dict in indicator_dict_variants.items():
        output_subdir = validation_result_path / variant_name
        metrics_df = validation.indicator_dict_to_df(metric_dict)
        pandas_utils.save_df(
            metrics_df,
            "",
            f"indicators_per_category",
            base_path=output_subdir,
        )
        # validation.get_metric_means(metric_dict, output_subdir)
        plot_path = output_subdir / "heatmaps"
        indicator_heatmaps.plot_indicators_by_profile_type(metrics_df, plot_path)
        indicator_heatmaps.plot_indicators_by_activity(metrics_df, plot_path)
        indicator_heatmaps.plot_profile_type_by_activity(metrics_df, plot_path)
    return

    # compare input and validation for each combination of profile types
    indicators_all_comb = validation.validate_all_combinations(
        input_statistics, validation_statistics
    )
    validation.save_file_per_indicator_per_combination(indicators_all_comb, output_path)
    indicator_heatmaps.plot_category_comparison(indicators_all_comb, plot_path)
    indicator_heatmaps.plot_category_comparison_per_activity(
        indicators_all_comb, plot_path
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
