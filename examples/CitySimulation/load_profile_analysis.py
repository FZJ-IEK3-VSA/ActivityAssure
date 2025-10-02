"""Plots for analyzing load profiles of a city simulation"""

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from matplotlib import pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import numpy as np
import seaborn as sns
import pandas as pd

from activityassure.loadprofiles.bdew_slp import BDEWProfileProvider
from activityassure.loadprofiles import utils as loadutils
from paths import DFColumnsLoad, LoadFiles


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


def datetime_to_hours(datetimes: pd.Series) -> pd.Series:
    """Turns a datetime series into a series
    of timedeltas from the start in hours

    :param datetimes: series of datetimes
    :return: series of time offsets in hours
    """
    time_axis = datetimes - datetimes.min()
    hours = time_axis.dt.total_seconds() / 3600
    return hours


def adapt_scaling(sumcurve: pd.DataFrame, col: str, unit: str = "W") -> str:
    """Scales a dataframe column inplace and returns the appropriate unit with
    prefix (k or M).

    :param sumcurve: the dataframe to adapt
    :param col: the name of the column to scale
    :param unit: the base unit, defaults to "W"
    :return: the unit with prefix
    """
    assert unit in ["W", "Wh"]
    if sumcurve[col].min() > 500:
        sumcurve[col] /= 1000  # convert W to kW
        unit = "kW"
    if sumcurve[col].min() > 500:
        sumcurve[col] /= 1000  # convert kW to MW
        unit = "MW"
    return unit


def stat_curves(path, result_dir, h25: pd.Series, with_max: bool = True):
    statpath = path / LoadFiles.DAYPROFILESTATS
    stats = pd.read_csv(statpath, index_col=0, parse_dates=[0], date_format="%H:%M:%S")
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    colormap = defaultdict(lambda: "grey", {"mean": "blue", "median": "green"})
    for stat in stats.columns:
        if not with_max and stat == "max":
            continue

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

    filename = "dayprofile_stats"
    if with_max:
        # when including the maximum, use a log scale
        ax.set_yscale("log")
    else:
        filename += "_no_max"

    # add axis labels
    hours_fmt = mdates.DateFormatter("%#H")
    ax.xaxis.set_major_formatter(hours_fmt)
    ax.xaxis.set_label_text("Uhrzeit [h]")
    ax.yaxis.set_label_text("Elektrische Last [W]")
    ax.legend()
    fig.savefig(result_dir / f"{filename}.svg")


def total_demand_distribution(path: Path, result_dir: Path, instance_name: str):
    total_demand = pd.read_csv(path / LoadFiles.TOTALS)
    total_demand.sort_values(DFColumnsLoad.TOTAL_DEMAND, inplace=True, ascending=False)

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)

    sns.lineplot(
        total_demand, ax=ax, y=DFColumnsLoad.TOTAL_DEMAND, x=range(len(total_demand))
    )
    ax2 = ax.twinx()
    sns.lineplot(
        total_demand,
        ax=ax2,  # type: ignore
        y=DFColumnsLoad.AVERAGE_LOAD,
        x=range(len(total_demand)),
    )
    ax.xaxis.set_label_text(instance_name)
    ax.yaxis.set_label_text("Stromverbrauch [kWh]")
    ax2.yaxis.set_label_text("Durchschnittliche Last [W]")
    fig.savefig(result_dir / "total_demand_per_profile.svg")


def sum_duration_curve(path: Path, result_dir: Path) -> pd.Series:
    sumcurve = pd.read_csv(path / LoadFiles.SUMPROFILE, parse_dates=[0])
    start_day = sumcurve[DFColumnsLoad.TIME].min().date()
    end_day = sumcurve[DFColumnsLoad.TIME].max().date()
    hours = datetime_to_hours(sumcurve[DFColumnsLoad.TIME])

    # sort by load to get the load duration curve
    sumcurve.sort_values(DFColumnsLoad.TOTAL_LOAD, inplace=True, ascending=False)

    # scale to a suitable unit
    unit = adapt_scaling(sumcurve, DFColumnsLoad.TOTAL_LOAD, "W")

    # create H25 standard profile load duration curve
    bdewprovider = BDEWProfileProvider()
    h25 = bdewprovider.get_profile_for_date_range(start_day, end_day)
    h25 = loadutils.kwh_to_w(h25)
    h25_sorted = h25.sort_values(ascending=False)

    # scale H25 to the same total demand
    h25_sorted = scale_profile(h25_sorted, sumcurve[DFColumnsLoad.TOTAL_LOAD])

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)

    sns.lineplot(
        sumcurve,
        ax=ax,
        y=DFColumnsLoad.TOTAL_LOAD,
        x=hours.values,
        label="Städtesimulation",
    )
    sns.lineplot(
        y=h25_sorted,
        ax=ax,
        label="H25 Standardprofil",
        x=np.linspace(0, hours.max(), len(h25_sorted)),
    )
    ax.xaxis.set_label_text("Dauer [h]")
    ax.yaxis.set_label_text(f"Elektrische Last [{unit}]")
    fig.savefig(result_dir / "sum_duration_curve.svg")

    # return the H25 profile for further use
    return h25


def simultaneity_curves(path: Path, result_dir: Path, instances: str):
    """
    Calculate simultaneity curves that show the diversity factor for increasingly
    many households of the dataset.

    :param path: path to postprocessed load profile data
    :param result_dir: directory to save the plot to
    """
    simultaneity = pd.read_csv(path / LoadFiles.SIMULTANEITY, index_col=0)

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)

    sns.lineplot(simultaneity, ax=ax, dashes=False)
    ax.xaxis.set_label_text(f"Anzahl {instances}")
    ax.yaxis.set_label_text("Gleichzeitigkeitsfaktor")

    # set a log scale and select appropriate axis limits
    ax.set_yscale("log")
    minval = min(10**-1, simultaneity.min().min())
    ax.set_ylim(minval, 1.1)
    # Define fixed ticks (avoid automatic exponent-style ticks)
    ticks = np.arange(0.1, 1.1, 0.1)
    ax.set_yticks(ticks)
    # Plain decimal format on y-axis
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.1f"))

    fig.tight_layout()
    fig.savefig(result_dir / "simultaneity.svg")


def create_load_stat_plots(path: Path, result_dir: Path, instances: str):
    result_dir.mkdir(parents=True, exist_ok=True)
    h25 = sum_duration_curve(path, result_dir)
    stat_curves(path, result_dir, h25, True)
    stat_curves(path, result_dir, h25, False)
    total_demand_distribution(path, result_dir, instances)
    simultaneity_curves(path, result_dir, instances)


def main(postproc_path: Path, plot_path: Path):
    hh_data_path = postproc_path / "loads/aggregated_household"
    create_load_stat_plots(hh_data_path, plot_path / "household", "Haushalte")
    house_data_path = postproc_path / "loads/aggregated_house"
    create_load_stat_plots(house_data_path, plot_path / "house", "Häuser")


if __name__ == "__main__":
    postproc_path = Path("D:/LPG/Results/scenario_julich-grosse-rurstr/Postprocessed")
    plot_path = postproc_path / "plots"
    main(postproc_path, plot_path)
