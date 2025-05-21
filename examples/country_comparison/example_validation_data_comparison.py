"""
Example that demonstrates usage of ETHOS.ActivityAssure for comparing
validation datasets of different countries.
"""

import logging
from pathlib import Path

from activityassure import utils, pandas_utils, validation
from activityassure import comparison_indicators
from activityassure import categorization_attributes
from activityassure.categorization_attributes import WorkStatus
from activityassure.hetus_data_processing import hetus_constants
from activityassure.input_data_processing import process_model_data
from activityassure.profile_category import ProfileCategory
from activityassure.visualizations import indicator_heatmaps, metric_comparison, time_statistics
from activityassure.validation_statistics import ValidationSet


@utils.timing
def validate(
    validation_data_path: Path,
    country1: str,
    country2: str,
    output_path: Path,
    compare_all_combinations: bool = False,
):
    """
    Load validation statistics and compare them using indicators and heatmaps.

    :param compare_all_combinations: if True, in attition to the normal
                                     per-category validation, all combinations
                                     of profile categories will be checked;
                                     defaults to False
    """
    # load LPG statistics and validation statistics
    validation_dataset_country1 = ValidationSet.load(
        validation_data_path, country=country1
    )
    validation_dataset_country2 = ValidationSet.load(
        validation_data_path, country=country2
    )

    # Prepare validation data, convert resolution
    if hetus_constants.get_resolution(country1) != hetus_constants.get_resolution(
        country2
    ):
        for _, v in (
            validation_dataset_country1.statistics
            | validation_dataset_country2.statistics
        ).items():
            # durations
            v.activity_durations.index = v.activity_durations.index.ceil("30min")
            v.activity_durations = v.activity_durations.resample("30min").sum()

            # interpolate probability profiles to 10 minute resolution
            if len(v.probability_profiles.columns) != 144:
                v.probability_profiles = comparison_indicators.resample_columns(
                    v.probability_profiles, 144
                )

    # compare input and validation data statistics per profile category
    indicator_dict_variants = validation.validate_per_category(
        validation_dataset_country1,
        validation_dataset_country2,
        output_path,
        ignore_country=True,
    )

    # save indicators and heatmaps for each indicator variant
    for variant_name, indicator_set in indicator_dict_variants.items():
        result_subdir = output_path / variant_name
        metrics_df = indicator_set.save(result_subdir / "indicators_per_category")

        activity_means = indicator_set.get_activity_indicators_averages()
        pandas_utils.save_df(
            activity_means,
            result_subdir,
            "indicator_means_per_activity",
        )

        # plot heatmaps to compare indicator values
        plot_path_heatmaps = result_subdir / "heatmaps"
        indicator_heatmaps.plot_indicators_by_activity(metrics_df, plot_path_heatmaps)
        indicator_heatmaps.plot_indicators_by_profile_type(
            metrics_df, plot_path_heatmaps
        )
        indicator_heatmaps.plot_profile_type_by_activity(metrics_df, plot_path_heatmaps)
        metric_comparison.plot_bar_plot_metrics_profile_type_activity(
            metrics_df, result_subdir / "bars", top_x=5
        )
        metric_comparison.plot_bar_plot_metrics_aggregated(
            metrics_df, result_subdir / "bars", "person_profile"
        )
        metric_comparison.plot_bar_plot_metrics_aggregated(
            activity_means, result_subdir / "bars", "activity"
        )

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


def merge_unemployed_categories(data_path: Path, result_path: Path):
    """Merge categories for work days and non-working days of unemployed people"""
    # load the statistics
    set = ValidationSet.load(data_path)
    # combine all 'unemployed' and 'retired' categories which only differ in day type
    WORK_TYPES_TO_MERGE = [WorkStatus.unemployed, WorkStatus.retired]
    mapping = {
        p: ProfileCategory(
            p.country,
            p.sex,
            p.work_status,
            categorization_attributes.DayType.undetermined,
        )
        for p in set.statistics.keys()
        if p.work_status in WORK_TYPES_TO_MERGE
    }
    set.merge_profile_categories(mapping)
    # save the aggregated statistics
    set.save(result_path)


def plot_total_time_bar_chart(validation_data_path: Path, national_stats_path: Path, countries: list[str], output_path: Path):
    # load LPG statistics and validation statistics
    datasets = [ValidationSet.load(
        validation_data_path, country=country
    ) for country in countries]
    validation_data1 = datasets[0]
    validation_data2 = datasets[1]

    # load the corresponding national statistics
    national_datasets = [ValidationSet.load(
        national_stats_path, country=country
    ) for country in countries]
    national_data1 = national_datasets[0]
    national_data2 = national_datasets[1]
    national_stats = national_data1.statistics | national_data2.statistics
    
    # Plot total time spent
    time_statistics.plot_total_time_spent(validation_data1.statistics, validation_data2.statistics, national_stats, output_path)


if __name__ == "__main__":
    country1 = "AT"
    country2 = "DE"

    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # validation statistics paths
    validation_stats_path = Path(
        "data/validation_data_sets/activity_validation_data_set"
    )
    validation_path_merged = Path(f"{validation_stats_path}_merged_daytypes")
    output_path = Path(f"data/country_comparison/{country1}-{country2}")

    # merge_unemployed_categories(validation_stats_path, validation_path_merged)

    # validate the input data using the statistics
    # validate(validation_path_merged, country1, country2, output_path)

    # paths for aggregated validation statistics
    national_stats_path = Path(f"{validation_path_merged}_national")
    output_path_national = Path(f"{output_path}_national")

    # validate the input data using the statistics on a national level
    process_model_data.aggregate_to_national_level(
        validation_path_merged, national_stats_path
    )
    # validate(national_stats_path, country1, country2, output_path_national)

    plot_total_time_bar_chart(validation_path_merged, national_stats_path, [country1, country2], output_path)