from datetime import timedelta
from pathlib import Path

from activityassure import utils
from activityassure import activity_mapping
from activityassure.input_data_processing import load_model_data
from activityassure.plausibility_checks import activity_profile_checks


def load_and_check_profiles(input_dir, mapping_file, person_trait_file):
    # define all input and output paths and other parameters
    profile_resolution = timedelta(minutes=1)

    # load and preprocess all input data
    full_year_profiles = load_model_data.load_activity_profiles_from_csv(
        input_dir, person_trait_file, profile_resolution, False
    )

    mapping, activities = activity_mapping.load_mapping_and_activities(mapping_file)
    for full_year_profile in full_year_profiles:
        full_year_profile.apply_activity_mapping(mapping)

    activity_profile_checks.check_activity_profiles(full_year_profiles)


if __name__ == "__main__":
    # preprocess the city simulation results to csv files
    input_dir = Path("D:/LPG/Results/scenario_city-julich_25_incomplete")
    result_dir = Path("data/city_preprocessed/") / input_dir.name

    utils.init_logging_stdout_and_file(Path("logs") / f"{input_dir.name}.txt")

    # load the csvs and check the profiles
    preprocessed_dir = Path("data/city_preprocessed")
    lpg_example_dir = Path("examples/LoadProfileGenerator/data")
    mapping_file = lpg_example_dir / "activity_mapping_city.json"
    person_trait_file = lpg_example_dir / "person_characteristics.json"

    load_and_check_profiles(result_dir, mapping_file, person_trait_file)
