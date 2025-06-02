"""Starts all result postprocessing of a single city simulation"""

import argparse
import logging
from pathlib import Path

from activityassure.preprocessing.lpg import activity_profiles

import paths
import load_profile_processing


def convert_activity_profiles(input_dir: Path, result_dir: Path, mapping_path: Path):
    """
    Converts all activity profiles generated in an LPG City Simulation to CSV files.

    :param input_dir: result directory of the city simulation
    :param result_dir: result directory to save the activity profiles to
    :param mapping_path: path to the activity mapping file to use
    """
    houses_dir = input_dir / "Houses"
    result_dir.mkdir(parents=True, exist_ok=True)
    # the Houses directory contains one subdirectory per house
    for house_dir in houses_dir.iterdir():
        assert house_dir.is_dir(), f"Unexpected file found: {house_dir}"
        # import each household database file from the house
        for db_file in house_dir.glob("Results.HH*.sqlite"):
            hh_name = db_file.stem.removeprefix("Results.")
            hh_id = f"{house_dir.name}_{hh_name}"
            activity_profiles.convert_activity_profile_from_db_to_csv(
                db_file, result_dir, mapping_path, hh_id
            )


def postprocess_city_results(city_result_dir: Path):
    postproc_dir = city_result_dir / paths.POSTPROCESSED_DIR
    load_profile_processing.main(city_result_dir, postproc_dir / "loads")

    mapping_file = Path("examples/LoadProfileGenerator/data/activity_mapping.json")
    activity_profiles_dir = postproc_dir / paths.ACTIVITY_PROFILES
    convert_activity_profiles(city_result_dir, activity_profiles_dir, mapping_file)


def main():
    # init logging
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        help="Root directory of the city simulation result data",
        default="/fast/home/d-neuroth/city_simulation_results/scenario_city-julich_25",
        required=False,
    )
    args = parser.parse_args()
    city_result_dir = Path(args.input)
    # city_result_dir = Path("D:/LPG/Results/scenario_julich-grosse-rurstr")
    assert city_result_dir.is_dir(), f"Invalid input directory: {city_result_dir}"
    logging.info(f"Postprocessing city simulation results in {city_result_dir}")

    postprocess_city_results(city_result_dir)


if __name__ == "__main__":
    main()
