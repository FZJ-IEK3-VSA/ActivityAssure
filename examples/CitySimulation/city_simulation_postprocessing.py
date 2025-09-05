"""Starts all result postprocessing of a single city simulation"""

import argparse
import logging
from pathlib import Path

from activityassure.preprocessing.lpg import activity_profiles
from activityassure import utils

from activityassure.raw_statistics import activity_statistics
from paths import SubDirs
import load_profile_processing
import activity_statistics_validation


def collect_household_dbs(result_dir: Path) -> dict[str, Path]:
    """
    Collects all household result databases from a city simulation. The
    databases are either sqlite files or directories of JSON files, depending
    on which output format was used in the LPG.

    :param result_dir: dictionary with paths to all household database files
    """
    houses_dir = result_dir / "Houses"
    house_dbs = {}
    # the Houses directory contains one subdirectory per house
    for house_dir in houses_dir.iterdir():
        assert house_dir.is_dir(), f"Unexpected file found: {house_dir}"
        # import each household database file from the house
        for db_file in house_dir.glob("Results.HH*"):
            assert db_file.is_dir() != (
                db_file.suffix == ".sqlite"
            ), "Invalid database format"
            hh_name = db_file.name.removeprefix("Results.").removesuffix(".sqlite")
            hh_id = f"{house_dir.name}_{hh_name}"
            house_dbs[hh_id] = db_file
    logging.info(f"Collected {len(house_dbs)} household database files")
    return house_dbs


@utils.timing
def convert_activity_profiles(
    hh_dbs: dict[str, Path], result_dir: Path, mapping_path: Path
):
    """
    Converts all activity profiles generated in an LPG City Simulation to CSV files.

    :param hh_dbs: dictionary with IDs and paths to all household database files
    :param result_dir: result directory to save the activity profiles to
    :param mapping_path: path to the activity mapping file to use
    """
    result_dir.mkdir(parents=True, exist_ok=True)
    # the Houses directory contains one subdirectory per house
    for hh_id, db_file in hh_dbs.items():
        activity_profiles.convert_activity_profile_from_db_to_csv(
            db_file, result_dir, mapping_path, hh_id
        )


@utils.timing
def postprocess_city_results(city_result_dir: Path):
    """
    Postprocesses the results of a city simulation to generate statistics and
    further data for the final validation

    :param city_result_dir: result directory of the city simulation
    """
    # process and aggregate load profile data for validation
    postproc_dir = city_result_dir / SubDirs.POSTPROCESSED_DIR
    load_profile_processing.main(city_result_dir, postproc_dir / SubDirs.LOADS_DIR)

    # collect all household result databases
    hh_dbs = collect_household_dbs(city_result_dir)

    # convert activity profiles from databases to csv format
    mapping_file = Path("examples/LoadProfileGenerator/data/activity_mapping.json")
    activity_profiles_dir = postproc_dir / SubDirs.ACTIVITY_PROFILES
    convert_activity_profiles(hh_dbs, activity_profiles_dir, mapping_file)

    # validate activity profiles with ActivityAssure
    statistics_path = postproc_dir / SubDirs.ACTIVITYASSURE
    activity_statistics_validation.calc_citysim_statistics_and_validate(
        activity_profiles_dir, statistics_path
    )

    # calculate raw activity statistics without mapping or aggregation
    activity_statistics.get_activity_statistics(
        activity_profiles_dir, postproc_dir / SubDirs.RAW_ACTIVITY_STATS
    )


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
