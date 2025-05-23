"""Create all plots for the validation of the city simulation in the dissertation."""

import argparse
import logging
from pathlib import Path

import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt

import paths
import activity_statistics_validation
import load_profile_analysis
import poi_validation
import calc_statistics
from activityassure.profile_category import ProfileCategory
from activityassure.ui import data_utils, datapaths, plots


def population_statistics(path: Path, result_dir: Path):
    # TODO: read json files and build dataframe from that instead
    path = Path(
        r"R:\repos\activityassure\data\city\postprocessed\scenario_city-julich_25\population_stats.csv"
    )
    validation_path = Path(
        "examples/CitySimulation/validation_data/Jülich_population_2022.json"
    )
    stats = pd.read_csv(path)

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    df_long = stats.melt(id_vars="measure", var_name="Dataset", value_name="Value")

    sns.barplot(x="measure", ax=ax, y="Value", hue="Dataset", data=df_long)
    fig.savefig(result_dir / "population_statistics_comparison.svg")
    plt.show()


def create_selected_activity_assure_plots():
    citysim_path = Path("data/city/validation/scenario_city-julich_25_merged")
    citysim_national = Path(f"{citysim_path}_national")
    # validation_national = Path(
    #     "data/validation_data_sets/activity_validation_data_set_national"
    # )

    # input_statistics = ValidationSet.load(citysim_path)

    plot_dir = Path("data/diss_validation_plots")

    profile_type = ProfileCategory("DE")
    filepath = data_utils.get_file_path(
        citysim_national / datapaths.prob_dir, profile_type
    )
    fig = plots.stacked_prob_curves(filepath)
    assert fig
    data_utils.save_plot(
        fig,
        "probability profiles",
        name="De",
        profile_type=profile_type,
        base_path=plot_dir,
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

    # path to a directory with preprocessed activitiy profiles in csv format
    postproc_dir = city_result_dir / paths.POSTPROCESSED_DIR
    plot_path = postproc_dir / "plots"
    load_profile_analysis.main(postproc_dir, plot_path)

    profile_dir = postproc_dir / paths.ACTIVITY_PROFILES
    statistics_path = postproc_dir / "activityassure_statistics"
    activity_statistics_validation.calc_citysim_statistics_and_validate(profile_dir, statistics_path)

    # TODO: futher validation steps:
    # - include POI validation
    # - add travel validation
    # - activity statistics, if that adds anything to this


if __name__ == "__main__":
    main()
