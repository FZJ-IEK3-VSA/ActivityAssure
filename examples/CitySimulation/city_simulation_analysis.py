"""Create all plots for the validation of the city simulation in the dissertation."""

import argparse
import logging
from pathlib import Path

from paths import SubDirs
import load_profile_analysis
import poi_validation
import geographic_analysis


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
        default="/fast/home/d-neuroth/city_simulation_results/scenario_juelich",
        required=False,
    )
    args = parser.parse_args()
    city_result_dir = Path(args.input)
    # city_result_dir = Path("R:/phd_dir/results/scenario_juelich_100_pharmacy")
    assert city_result_dir.is_dir(), f"Invalid input directory: {city_result_dir}"
    logging.info(f"Analysing city simulation results in {city_result_dir}")

    # get the path to the scenario directory
    scenario_dir = city_result_dir / "scenario"
    assert (
        scenario_dir.is_dir()
    ), f"Scenario directory not found or symlink missing: {scenario_dir}"

    # path to a directory with preprocessed activitiy profiles in csv format
    postproc_dir = city_result_dir / SubDirs.POSTPROCESSED_DIR
    plot_path = postproc_dir / SubDirs.PLOTS

    load_profile_analysis.main(postproc_dir, plot_path / SubDirs.LOADS_DIR)
    poi_validation.main(city_result_dir, plot_path / SubDirs.POIS)
    geographic_analysis.main(scenario_dir, city_result_dir, plot_path / SubDirs.MAPS)


if __name__ == "__main__":
    main()
