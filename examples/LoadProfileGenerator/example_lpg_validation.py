"""
Example script for validation of the LoadProfileGenerator
"""

from datetime import timedelta
import logging
from pathlib import Path

from activity_validator import activity_mapping, utils, pandas_utils, validation
from activity_validator.input_data_processing import process_model_data
from activity_validator.visualizations import indicator_heatmaps
from activity_validator.validation_statistics import ValidationSet


def merge_activities(
    statistics_path: Path, merging_path: Path, new_path: Path | None = None
):
    """
    Loads validation statistics and merges activities according to the specified file.
    The translated statistics are then saved with a new name

    :param statistics_path: path of validation statistics to adapt
    :param merging_path: path of the merging file to use
    :param new_name: new name for the adapted statistics, by default appends "_mapped"
    """
    # load statistics and merging map and apply the merging
    validation_statistics = ValidationSet.load(statistics_path)
    mapping, _ = activity_mapping.load_mapping_and_activities(merging_path)
    validation_statistics.map_statistics_activities(mapping)
    # determine the new file name for the mapped statistics
    new_path = new_path or f"{statistics_path}_mapped"
    # save the mapped statistics
    validation_statistics.save(new_path)


@utils.timing
def validate(
    input_path: Path, validation_path: Path, compare_all_combinations: bool = False
):
    """
    Load input and validation statistics and compare them
    using indicators and heatmaps.

    :param compare_all_combinations: if True, in attition to the normal
                                     per-category validation, all combinations
                                     of profile categories will be checked;
                                     defaults to False
    """
    # load LPG statistics and validation statistics
    input_statistics = ValidationSet.load(input_path)
    validation_statistics = ValidationSet.load(validation_path)

    # compare input and validation data statistics per profile category
    indicator_dict_variants = validation.validate_per_category(
        input_statistics, validation_statistics, input_path
    )
    validation_result_path = input_path / "validation_results"

    # save indicators and heatmaps for each indicator variant
    for variant_name, metric_dict in indicator_dict_variants.items():
        result_subdir = validation_result_path / variant_name
        metrics_df = validation.indicator_dict_to_df(metric_dict)
        pandas_utils.save_df(
            metrics_df,
            "",
            "indicators_per_category",
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
            indicators_all_combinations, input_path
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

    # define all input and output paths and other parameters
    # input data paths
    lpg_input_dir = Path("examples/LoadProfileGenerator/data")
    input_data_path = lpg_input_dir / "preprocessed"
    merging_file = lpg_input_dir / "activity_merging.json"
    mapping_file = lpg_input_dir / "activity_mapping.json"
    person_trait_file = lpg_input_dir / "person_characteristics.json"
    # statistics paths
    validation_stats_path = Path("data/validation_data_sets/full")
    merged_validation_stats_path = Path("data/validation_data_sets/full_mapped")
    input_stats_path = Path("data/validation/lpg_per_person_local")
    # other parameters
    profile_resolution = timedelta(minutes=1)

    # the LoadProfileGenerator simulates cooking and eating as one activity, therefore these
    # two activities must be merged in the validation statistics
    merge_activities(validation_stats_path, merging_file, merged_validation_stats_path)

    # calculate statistics for the input model data
    input_statistics = process_model_data.process_model_data(
        input_data_path,
        mapping_file,
        person_trait_file,
        profile_resolution,
        categories_per_person=True,
    )
    # save the created statistics
    input_statistics.save(input_stats_path)

    # validate the input data using the statistics
    validate(input_stats_path, merged_validation_stats_path)
