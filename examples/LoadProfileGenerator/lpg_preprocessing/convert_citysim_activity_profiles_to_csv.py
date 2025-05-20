"""
Converts all activity profiles generated in an LPG City Simulation to CSV files.
"""

import logging
from pathlib import Path

import convert_lpg_activity_profile_to_csv as lpg_profile_conversion
from activityassure.preprocessing.lpg import activity_profiles


def convert_activity_profiles(input_dir: Path, result_dir: Path, mapping_path: Path):
    houses_dir = input_dir / "Houses"
    result_dir.mkdir(parents=True, exist_ok=True)
    # the Houses directory contains one subdirectory per house
    for house_dir in houses_dir.iterdir():
        assert house_dir.is_dir(), f"Unexpected file found: {house_dir}"
        # import each household database file from the house
        for db_file in house_dir.glob("Results.HH*.sqlite"):
            activity_profiles.convert_activity_profile_from_db_to_csv(
                db_file, result_dir, mapping_path, house_dir.name
            )


if __name__ == "__main__":
    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # preprocess the city simulation results to csv files
    input_dir = Path("D:/LPG/Results/scenario_city-julich")
    # input_dir = Path("R:/city_simulation_results/scenario_city-julich_25")
    result_dir = Path("data/city_preprocessed/") / input_dir.name

    # load the csvs and check the profiles
    lpg_example_dir = Path("examples/LoadProfileGenerator/data")
    mapping_file = lpg_example_dir / "activity_mapping_city.json"

    convert_activity_profiles(input_dir, result_dir, mapping_file)
