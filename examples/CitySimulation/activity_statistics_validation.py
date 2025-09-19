"""
Example that demonstrates usage of ETHOS.ActivityAssure by validating
the city simulation of the LoadProfileGenerator.
"""

from datetime import timedelta
import logging
from pathlib import Path

from activityassure import validation
from activityassure.input_data_processing import process_model_data, process_statistics
from activityassure.profile_category import ProfileCategory
from activityassure.validation_statistics import ValidationSet
from activityassure.visualizations import time_statistics

from paths import SubDirs


def merge_statistics(
    activity_merging_file: Path,
    validation_path: Path,
    validation_path_merged: Path,
    custom_weights: dict[ProfileCategory, float | None] | None = None,
):
    """Applies all relevant activity and category mergings to a set of statistics.

    :param activity_merging_file: activity merging file
    :param validation_path: input statistics path
    :param validation_path_merged: output path for merged statistics
    :param custom_weights: optional custom weights to use for merging
    """
    statistics = ValidationSet.load(validation_path)
    if custom_weights:
        statistics.set_custom_weights(custom_weights, True)

    # the LoadProfileGenerator simulates cooking and eating as one activity, therefore these
    # two activities must be merged in the validation statistics
    process_statistics.merge_activities(statistics, activity_merging_file)

    # merge work and non-work days for unemployed and retired categories
    process_statistics.merge_unemployed_categories(statistics)
    statistics.save(validation_path_merged)


def calc_citysim_statistics_and_validate(
    activity_profiles_dir: Path, city_stats_path: Path
):
    """Calculates ActivityAssure statistics out of activity profiles from
    a CitySimulation, merges HETUS validation statistics to match, and
    carries out the default indicator validation procedure.

    :param activity_profiles_dir: directory with activity profiles from
                                   the CitySimulation
    :param city_stats_path: output paht for the generated statistics
    : param scenario_dir: path to the scenario directory of the simulation
    """
    # define all input and output paths and other parameters
    profile_resolution = timedelta(minutes=1)

    # additional files with mappings and person information
    lpg_example_data_dir = Path("examples/LoadProfileGenerator/data")
    merging_file = lpg_example_data_dir / "activity_merging.json"
    mapping_file = lpg_example_data_dir / "activity_mapping.json"
    person_trait_file = lpg_example_data_dir / "person_characteristics.json"

    # validation statistics paths
    validation_stats_path = Path(
        "data/validation_data_sets/activity_validation_data_set"
    )
    validation_stats_path_merged = Path(f"{validation_stats_path}_merged")

    # calculate statistics for the input model data
    input_statistics = process_model_data.process_model_data(
        activity_profiles_dir,
        mapping_file,
        person_trait_file,
        profile_resolution,
        categories_per_person=False,
    )
    # save the created statistics
    input_statistics.save(city_stats_path)

    # apply the statistics merging to the city simulation results
    city_stats_path_merged = Path(f"{city_stats_path}_merged")
    merge_statistics(
        merging_file,
        city_stats_path,
        city_stats_path_merged,
    )
    input_weights = input_statistics.get_weight_dict()

    # apply the merging to the validation data as well, using the input weights
    # to get a matching population
    merge_statistics(
        merging_file,
        validation_stats_path,
        validation_stats_path_merged,
        input_weights,
    )

    # validate the input data using the statistics
    validation.default_validation(city_stats_path_merged, validation_stats_path_merged)

    # additionally, aggregate both statistics to national level and validate with that
    validation_national = Path(f"{validation_stats_path_merged}_national")
    process_statistics.aggregate_to_national_level(
        validation_stats_path_merged, validation_national
    )
    citysim_national = Path(f"{city_stats_path_merged}_national")
    process_statistics.aggregate_to_national_level(
        city_stats_path_merged, citysim_national
    )

    validation.default_validation(citysim_national, validation_national)

    # create stacked bar charts for total time use
    plot_dir = city_stats_path.parent / SubDirs.PLOTS / SubDirs.ACTIVITIES
    names = ["TUS", "LPG"]
    plotpath = plot_dir / "stacked_bar_time_spent.svg"
    plotpath_nat = plot_dir / "stacked_bar_time_spent_national.svg"
    time_statistics.plot_total_time_bar_chart(
        validation_stats_path_merged, city_stats_path_merged, names, plotpath
    )
    time_statistics.plot_total_time_bar_chart(
        validation_national, citysim_national, names, plotpath_nat
    )


def main():
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    postproc_path = Path("C:/LPG/Results/scenario_julich-grosse-rurstr/Postprocessed")
    profiles_dir = postproc_path / "activity_profiles"
    statistics_path = postproc_path / "activityassure_statistics"

    calc_citysim_statistics_and_validate(profiles_dir, statistics_path)


if __name__ == "__main__":
    main()
