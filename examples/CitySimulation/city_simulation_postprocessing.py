"""Starts all result postprocessing of a single city simulation"""

import argparse
import logging
from pathlib import Path

from activityassure import utils

from activityassure.preprocessing.lpg import activity_profiles as lpgprofiles
from activityassure.raw_statistics import activity_statistics
from paths import SubDirs
import transport_processing
import load_profile_processing
import activity_statistics_validation


@utils.timing
def postprocess_city_results(city_result_dir: Path):
    """
    Postprocesses the results of a city simulation to generate statistics and
    further data for the final validation

    :param city_result_dir: result directory of the city simulation
    """
    # collect all household result databases
    hh_dbs = lpgprofiles.collect_household_dbs(city_result_dir)

    # process travel-related data for validation
    postproc_dir = city_result_dir / SubDirs.POSTPROCESSED_DIR
    transport_processing.main(city_result_dir, postproc_dir / SubDirs.TRANSPORT, hh_dbs)

    # process and aggregate load profile data for validation
    load_profile_processing.main(city_result_dir, postproc_dir / SubDirs.LOADS_DIR)

    # convert activity profiles from databases to csv format
    mapping_file = Path("examples/LoadProfileGenerator/data/activity_mapping.json")
    activity_profiles_dir = postproc_dir / SubDirs.ACTIVITY_PROFILES
    lpgprofiles.convert_activity_profiles(hh_dbs, activity_profiles_dir, mapping_file)

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
