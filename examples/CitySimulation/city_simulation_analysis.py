"""Create all plots for the validation of the city simulation in the dissertation."""

import argparse
import logging
from pathlib import Path

import paths
import activity_statistics_validation
import load_profile_analysis
import poi_validation
import calc_statistics


def main():
    # init logging
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.INFO,
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
    logging.info(f"Analysing city simulation results in {city_result_dir}")

    # path to a directory with preprocessed activitiy profiles in csv format
    postproc_dir = city_result_dir / paths.POSTPROCESSED_DIR
    plot_path = postproc_dir / "plots"

    load_profile_analysis.main(postproc_dir, plot_path)

    profile_dir = postproc_dir / paths.ACTIVITY_PROFILES
    statistics_path = postproc_dir / "activityassure_statistics"
    activity_statistics_validation.calc_citysim_statistics_and_validate(
        profile_dir, statistics_path
    )

    # TODO: futher validation steps:
    # - include POI validation
    # - add travel validation
    # - activity statistics, if that adds anything to this


if __name__ == "__main__":
    main()
