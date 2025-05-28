"""Plots for analyzing load profiles of a city simulation"""

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from matplotlib import pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import seaborn as sns
import pandas as pd

from activityassure.loadprofiles.bdew_slp import BDEWProfileProvider
from paths import DFColumns, LoadFiles


def scale_profile(profile_to_scale, reference_profile):
    """
    Scales a profile to match the total sum of a reference profile.
    Also considers different resolutions of the profiles.

    :param profile_to_scale: the profile that should be scaled
    :param reference_profile: the profile to scale to
    :return: the scaled profile
    """
    factor = reference_profile.sum() / profile_to_scale.sum()
    # adjust to different resolutions so the curves can be compared
    factor *= len(profile_to_scale) / len(reference_profile)
    profile_to_scale *= factor
    return profile_to_scale


def stat_curves(path, result_dir, h25: pd.Series):
    statpath = path / LoadFiles.MEANDAY_STATS
    stats = pd.read_csv(statpath, index_col=0, parse_dates=[0], date_format="%H:%M:%S")
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    colormap = defaultdict(lambda: "grey", {"mean": "blue", "median": "green"})
    for stat in stats.columns:
        # if stat == "max":
        #     continue

        ax.plot(stats[stat], label=stat, color=colormap[stat])

    # plot the H25 average day profile
    h25meanday = h25.groupby(h25.index.time).mean()  # type: ignore
    # adapt the index to match the stats index for plotting
    day = stats.index[0].date()
    h25meanday.index = pd.to_datetime(
        [datetime.combine(day, time) for time in h25meanday.index]
    )
    # scale h25 to the mean profile
    h25meanday = scale_profile(h25meanday, stats["mean"])
    ax.plot(h25meanday, label="H25 Standardprofil", color="red")

    # add axis labels
    hours_fmt = mdates.DateFormatter("%#H")
    ax.xaxis.set_major_formatter(hours_fmt)
    ax.xaxis.set_label_text("Uhrzeit [h]")
    ax.yaxis.set_label_text("Elektrische Last [kWh]")
    ax.legend()
    fig.savefig(result_dir / "mean_day_stats.svg")


def total_load_distribution(path: Path, result_dir: Path):
    totals = pd.read_csv(path / LoadFiles.TOTALS)
    totals.sort_values(DFColumns.LOAD, inplace=True, ascending=False)

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)

    sns.lineplot(totals, ax=ax, y=DFColumns.LOAD, x=range(len(totals)))
    ax.set_xticklabels([])
    ax.xaxis.set_label_text("Häuser")
    ax.yaxis.set_label_text("Elektrische Last [kWh]")
    fig.savefig(result_dir / "profile_sums.svg")


def sum_duration_curve(path: Path, result_dir: Path) -> pd.Series:
    sumcurve = pd.read_csv(path / LoadFiles.SUMPROFILE, parse_dates=[0])
    start_day = sumcurve[DFColumns.TIME].min().date()
    end_day = sumcurve[DFColumns.TIME].max().date()

    # sort by load to get the load duration curve
    sumcurve.sort_values(DFColumns.LOAD, inplace=True, ascending=False)

    # create H25 standard profile load duration curve
    bdewprovider = BDEWProfileProvider()
    h25 = bdewprovider.get_profile_for_date_range(start_day, end_day)
    h25_sorted = h25.sort_values(ascending=False)

    # scale H25 to the same total demand
    h25_sorted = scale_profile(h25_sorted, sumcurve[DFColumns.LOAD])

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)

    sns.lineplot(sumcurve, ax=ax, y=DFColumns.LOAD, x=range(len(sumcurve)))
    sns.lineplot(
        y=h25_sorted,
        ax=ax,
        label="H25 Standardprofil",
        x=np.linspace(0, len(sumcurve), len(h25_sorted)),
    )
    ax.xaxis.set_label_text("Dauer [min]")  # TODO: not correct for 600s HH data
    ax.yaxis.set_label_text("Elektrische Last [kWh]")
    fig.savefig(result_dir / "sum_duration_curve.svg")

    # return the H25 profile for further use
    return h25


def simultaneity_curves(path: Path, result_dir: Path):
    """
    Calculate simultaneity curves that show the simultaneity factor for increasingly
    many households of the dataset.

    :param path: path to postprocessed load profile data
    :param result_dir: directory to save the plot to
    """
    simultaneity = pd.read_csv(path / LoadFiles.SIMULTANEITY, index_col=0)

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)

    sns.lineplot(simultaneity, ax=ax)
    ax.xaxis.set_label_text("Anzahl Haushalte")
    ax.yaxis.set_label_text("Gleichzeitigkeitsfaktor")
    fig.savefig(result_dir / "simultaneity.svg")


def create_load_stat_plots(path: Path, result_dir: Path):
    result_dir.mkdir(parents=True, exist_ok=True)
    h25 = sum_duration_curve(path, result_dir)
    stat_curves(path, result_dir, h25)
    total_load_distribution(path, result_dir)
    simultaneity_curves(path, result_dir)


def main(postproc_path: Path, plot_path: Path):
    hh_data_path = postproc_path / "loads/aggregated_household"
    create_load_stat_plots(hh_data_path, plot_path / "household")
    house_data_path = postproc_path / "loads/aggregated_house"
    create_load_stat_plots(house_data_path, plot_path / "house")


if __name__ == "__main__":
    postproc_path = Path("D:/LPG/Results/scenario_julich-grosse-rurstr/Postprocessed")
    plot_path = postproc_path / "plots"
    main(postproc_path, plot_path)
