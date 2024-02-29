"""
Example script for validation of the LoadProfileGenerator
"""

import logging
from pathlib import Path

from activity_validator import activity_mapping, utils, pandas_utils, validation
from activity_validator.input_data_processing import process_model_data
from activity_validator.visualizations import indicator_heatmaps
from activity_validator.validation_statistics import ValidationSet


@utils.timing
def create_statistics_set(base_path: Path):
    """
    Generate the statistics set needed for validation out of the
    activity profile data from the LoadProfileGenerator.
    """
    LPG_EXAMPLE_PATH = Path("examples/LoadProfileGenerator")
    INPUT_DATA_PATH = base_path / "lpg_simulations/preprocessed"
    LPG_MAPPING_FILE = LPG_EXAMPLE_PATH / "activity_mapping_lpg.json"
    PERSON_TRAIT_FILE = LPG_EXAMPLE_PATH / "person_characteristics.json"

    VALIDATION_STATS_PATH = (
        base_path / "validation data sets/country_sex_work status_day type"
    )

    OUTPUT_PATH = base_path / "lpg_validation"

    # load validation data statistics
    validation_statistics = ValidationSet.load(VALIDATION_STATS_PATH)

    # calculate statistics for the input model data
    input_statistics = process_model_data.process_model_data(
        INPUT_DATA_PATH,
        LPG_MAPPING_FILE,
        PERSON_TRAIT_FILE,
        validation_statistics.activities,
    )

    # if necessary, apply another mapping to merge activities
    CUSTOM_MAPPING_FILE = LPG_EXAMPLE_PATH / "activity_mapping_validation_lpg.json"
    if CUSTOM_MAPPING_FILE is not None:
        mapping, _ = activity_mapping.load_mapping_and_activities(CUSTOM_MAPPING_FILE)
        input_statistics.map_statistics_activities(mapping)
        validation_statistics.map_statistics_activities(mapping)

        # the validation statistics have been changed and need to be saved again
        mapped_validation_path = Path(f"{VALIDATION_STATS_PATH}_mapped")
        validation_statistics.save(mapped_validation_path)
        assert input_statistics.activities == validation_statistics.activities

    # save the created statistics
    input_statistics.save(OUTPUT_PATH)


@utils.timing
def validate(base_path: Path, compare_all_combinations: bool = False):
    """
    Load input and validation statistics and compare them
    using indicators and heatmaps.

    :param compare_all_combinations: if True, in attition to the normal
                                     per-category validation, all combinations
                                     of profile categories will be checked;
                                     defaults to False
    """
    lpg_statistics_path = base_path / "lpg_validation"
    valdiation_statistics_path = (
        base_path / "validation data sets/country_sex_work status_day type_mapped"
    )

    # load LPG statistics and validation statistics
    input_statistics = ValidationSet.load(lpg_statistics_path)
    validation_statistics = ValidationSet.load(valdiation_statistics_path)

    # compare input and validation data statistics per profile category
    indicator_dict_variants = validation.validate_per_category(
        input_statistics, validation_statistics, lpg_statistics_path
    )
    validation_result_path = lpg_statistics_path / "validation_results"

    # save indicators and heatmaps for each indicator variant
    for variant_name, metric_dict in indicator_dict_variants.items():
        result_subdir = validation_result_path / variant_name
        metrics_df = validation.indicator_dict_to_df(metric_dict)
        pandas_utils.save_df(
            metrics_df,
            "",
            f"indicators_per_category",
            base_path=result_subdir,
        )

        # plot heatmaps to compare indicator values
        plot_path = result_subdir / "heatmaps"
        indicator_heatmaps.plot_indicators_by_profile_type(metrics_df, plot_path)
        indicator_heatmaps.plot_indicators_by_activity(metrics_df, plot_path)
        indicator_heatmaps.plot_profile_type_by_activity(metrics_df, plot_path)

    if compare_all_combinations:
        # compare statistics for each combination of profile categories
        indicators_all_combinations = validation.validate_all_combinations(
            input_statistics, validation_statistics
        )
        validation.save_file_per_indicator_per_combination(
            indicators_all_combinations, lpg_statistics_path
        )

        # plot heatmaps to compare the different categories to each other
        indicator_heatmaps.plot_category_comparison(
            indicators_all_combinations, plot_path
        )
        indicator_heatmaps.plot_category_comparison_per_activity(
            indicators_all_combinations, plot_path
        )


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    BASE_RESULT_PATH = Path("data")
    create_statistics_set(BASE_RESULT_PATH)
    validate(BASE_RESULT_PATH)
