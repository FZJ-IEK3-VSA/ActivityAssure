"""
Example that demonstrates usage of ETHOS.ActivityAssure for comparing
validation datasets of different countries.
"""

import logging
from pathlib import Path

from activityassure import utils, pandas_utils, validation
from activityassure.hetus_data_processing import hetus_constants
from activityassure.visualizations import indicator_heatmaps, metric_comparison
from activityassure.validation_statistics import ValidationSet


@utils.timing
def validate(
    validation_data_path: Path,
    country1: str,
    country2: str,
    output_path: Path,
    compare_all_combinations: bool = False
):
    """
    Load validation statistics and compare them using indicators and heatmaps.

    :param compare_all_combinations: if True, in attition to the normal
                                     per-category validation, all combinations
                                     of profile categories will be checked;
                                     defaults to False
    """
    # load LPG statistics and validation statistics
    validation_dataset_country1 = ValidationSet.load(validation_data_path, country=country1)
    validation_dataset_country2 = ValidationSet.load(validation_data_path, country=country2)

    # Prepare validation data, convert resolution
    if hetus_constants.get_resolution(country1) != hetus_constants.get_resolution(country2):
        for _, v in (validation_dataset_country1.statistics | validation_dataset_country2.statistics).items():
            # durations
            v.activity_durations.index = v.activity_durations.index.ceil('30min')
            v.activity_durations = v.activity_durations.resample('30min').sum()

            # probability profiles
            # 10 minute resolution with target 30 minutes -> merge three columns
            # 15 minute resolution with target 30 minutes -> merge two columns
            current_resolution = 10 if len(v.probability_profiles.columns) == 144 else 15
            v.probability_profiles.columns = [i * current_resolution for i in range(0, len(v.probability_profiles.columns))]
            v.probability_profiles = v.probability_profiles.T.groupby(lambda x: x // 30 * 30).mean().T
            v.probability_profiles.columns = [f"MACT{i}" for i in range(1, len(v.probability_profiles.columns)+1)]


    # compare input and validation data statistics per profile category
    indicator_dict_variants = validation.validate_per_category(
        validation_dataset_country1, validation_dataset_country2, output_path, ignore_country=True
    )

    # save indicators and heatmaps for each indicator variant
    for variant_name, metric_dict in indicator_dict_variants.items():
        result_subdir = output_path / variant_name
        metrics_df = validation.indicator_dict_to_df(metric_dict)
        pandas_utils.save_df(
            metrics_df,
            result_subdir,
            "indicators_per_category",
        )

        # plot heatmaps to compare indicator values
        plot_path_heatmaps = result_subdir / "heatmaps"
        indicator_heatmaps.plot_indicators_by_activity(metrics_df, plot_path_heatmaps)
        indicator_heatmaps.plot_indicators_by_profile_type(metrics_df, plot_path_heatmaps)
        indicator_heatmaps.plot_profile_type_by_activity(metrics_df, plot_path_heatmaps)
        metric_comparison.plot_bar_plot_metrics_profile_type_activity(metrics_df, result_subdir / "bars", top_x=5)

    if compare_all_combinations:
        # compare statistics for each combination of profile categories
        indicators_all_combinations = validation.validate_all_combinations(
            validation_dataset_country1, validation_dataset_country2
        )
        validation.save_file_per_indicator_per_combination(
            indicators_all_combinations, validation_data_path
        )

        # plot heatmaps to compare the different categories to each other
        indicator_heatmaps.plot_category_comparison(
            indicators_all_combinations, plot_path_heatmaps
        )
        indicator_heatmaps.plot_category_comparison_per_activity(
            indicators_all_combinations, plot_path_heatmaps
        )


if __name__ == "__main__":
    country1="AT"
    country2="DE"

    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # validation statistics paths
    validation_stats_path = Path("data/validation_data_sets/activity_validation_data_set")
    output_path = Path(f"../../data/country_comparison/{country1}-{country2}")

    # validate the input data using the statistics
    validate(validation_stats_path, country1, country2, output_path)
