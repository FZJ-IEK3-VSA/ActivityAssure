from datetime import timedelta
import logging
from pathlib import Path

from activityassure import utils
from activityassure import activity_mapping
from activityassure.input_data_processing import load_model_data
from activityassure.plausibility_checks import activity_profile_checks


@utils.timing
def calc_activity_statistics(input_dir, mapping_file, person_trait_file, output_dir):
    # define all input and output paths and other parameters
    profile_resolution = timedelta(minutes=1)

    # load and preprocess all input data
    full_year_profiles = load_model_data.load_activity_profiles_from_csv(
        input_dir, person_trait_file, profile_resolution, False
    )

    mapping, _ = activity_mapping.load_mapping_and_activities(mapping_file)
    for full_year_profile in full_year_profiles:
        full_year_profile.apply_activity_mapping(mapping)
    logging.info(f"Collecting statistics for {len(full_year_profiles)} profiles")

    # activity_profile_checks.run_checks_for_activity_profiles(full_year_profiles)
    activities = ["sleep", "vacation", "work", "travel", "idle", "other"]
    for activity in activities:
        statistics_file = output_dir / f"{activity}.csv"
        activity_profile_checks.collect_profile_stats(
            full_year_profiles, statistics_file, activity
        )
        activity_profile_checks.plot_profile_stats(statistics_file)


if __name__ == "__main__":
    # preprocess the city simulation results to csv files
    data_dir = Path("data/city/preprocessed/scenario_city-julich_mini")

    logger = utils.init_logging_stdout_and_file(Path("logs") / f"{data_dir.name}.txt")
    logger.setLevel(logging.DEBUG)

    # load the csvs and check the profiles
    example_data_dir = Path("examples/CitySimulation/data")
    mapping_file = example_data_dir / "activity_mapping_city.json"
    person_trait_file = Path("examples/LoadProfileGenerator/data/person_characteristics.json")

    output_dir = Path("data/city/validation_statistics") / data_dir.name

    calc_activity_statistics(data_dir, mapping_file, person_trait_file, output_dir)
