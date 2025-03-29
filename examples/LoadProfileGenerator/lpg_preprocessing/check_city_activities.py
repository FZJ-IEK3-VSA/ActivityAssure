from datetime import timedelta
import logging
from pathlib import Path

from tqdm import tqdm

from activityassure import activity_mapping
from activityassure.input_data_processing import load_model_data
from activityassure.plausibility_checks import activity_profile_checks
import convert_lpg_activity_profile_to_csv as lpg_profile_conversion


def convert_activity_profiles(input_dir: Path, result_dir: Path, mapping_path: Path):
    houses_dir = input_dir / "Houses"
    result_dir.mkdir(parents=True, exist_ok=True)
    # the Houses directory contains one subdirectory per house
    for house_dir in houses_dir.iterdir():
        assert house_dir.is_dir(), f"Unexpected file found: {house_dir}"
        # import each household database file from the house
        for db_file in house_dir.glob("Results.HH*.sqlite"):
            # try:
            lpg_profile_conversion.convert_activity_profile_from_db_to_csv(
                db_file, result_dir, mapping_path, house_dir.name
            )
            # except Exception as e:
            #     print(f"Exception occurred: {e}")


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
    logging.basicConfig(
        format="%(message)s",
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # preprocess the city simulation results to csv files
    input_dir = Path(r"D:\LPG\Results\scenario_city-heimbach-street-lindenweg")
    result_dir = Path("data/city_preprocessed/")

    # load the csvs and check the profiles
    preprocessed_dir = Path("data/city_preprocessed")
    lpg_example_dir = Path("examples/LoadProfileGenerator/data")
    mapping_file = lpg_example_dir / "activity_mapping.json"
    person_trait_file = lpg_example_dir / "person_characteristics.json"

    convert_activity_profiles(input_dir, result_dir, mapping_file)

    load_and_check_profiles(preprocessed_dir, mapping_file, person_trait_file)
