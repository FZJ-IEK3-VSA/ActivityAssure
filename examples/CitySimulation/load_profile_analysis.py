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


def adapt_scaling(sumcurve: pd.DataFrame, col: str, unit: str = "W") -> tuple[str, int]:
    """Scales a dataframe column inplace and returns the appropriate unit with
    prefix (k or M).

    :param sumcurve: the dataframe to adapt
    :param col: the name of the column to scale
    :param unit: the base unit, defaults to "W"
    :return: the unit with prefix
    """
    assert unit in ["W", "Wh"]
    factor = 1
    if sumcurve[col].min() > 500:
        sumcurve[col] /= 1000  # convert W to kW
        factor *= 1000
        unit = "kW"
    if sumcurve[col].min() > 500:
        sumcurve[col] /= 1000  # convert kW to MW
        factor *= 1000
        unit = "MW"
    return unit, factor


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
    fig.tight_layout()
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
    fig.tight_layout()
    fig.savefig(result_dir / "total_demand_per_profile.svg")


def total_demand_distribution_by_hh_type(path: Path, result_dir: Path, instances: str):
    if instances != "Haushalte":
        return  # these plots are only for households

    # determine the corresponding scenario directory using the symlink
    scenario_dir = path.parents[2] / "scenario"
    assert scenario_dir.is_dir(), f"Scenario directory not found: {scenario_dir}"
    hh_data_dir = scenario_dir / "statistics/households"

    # load size and type info for each household
    with open(hh_data_dir / "size_of_each_hh.json", "r") as f:
        size_per_hh = json.load(f)
    with open(hh_data_dir / "type_of_each_hh.json", "r") as f:
        type_per_hh = json.load(f)
        type_per_hh = {k: v.split(" ")[0] for k, v in type_per_hh.items()}

    # load the total demands
    total_demand = pd.read_csv(path / LoadFiles.TOTALS)
    total_demand.sort_values(DFColumnsLoad.TOTAL_DEMAND, inplace=True, ascending=False)

    size_col = "Anzahl Personen"
    total_demand[size_col] = total_demand["Household"].map(size_per_hh)
    type_col = "Typ"
    total_demand[type_col] = total_demand["Household"].map(type_per_hh)
    df = total_demand  # shorter name

    # Define bin width for total demand
    bin_width = 400

    # Determine min and max to create bins
    min_val = 0
    max_val = df[DFColumnsLoad.TOTAL_DEMAND].max()

    # Create bin edges
    bins = np.arange(min_val, max_val + bin_width, bin_width)  # Bin the data
    df["binned"] = pd.cut(df[DFColumnsLoad.TOTAL_DEMAND], bins=bins, right=False)

    # Count values in each bin
    bin_counts = df["binned"].value_counts().sort_index().reset_index()
    bin_counts.columns = ["Range", "Count"]

    # Optionally, use bin centers for a cleaner x-axis
    bin_counts["Center"] = bin_counts["Range"].apply(lambda x: x.left + bin_width / 2)
    bin_counts["Center_rd"] = bin_counts["Center"].round().astype(np.int32)

    # plot load per household size as stacked bar chart
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)

    pivot = df.groupby(["binned", size_col]).size().unstack(fill_value=0)
    # use range centers as x labels
    pivot.index = bin_counts["Center_rd"]  # type: ignore
    pivot.plot(kind="bar", stacked=True, ax=ax)
    ax.set_xlabel("Jährlicher Verbrauch [kWh]")
    ax.set_ylabel("Anzahl Haushalte")
    plt.xticks(rotation=90)
    fig.tight_layout()
    fig.savefig(result_dir / "total_demand_dist_by_size_stacked.svg")

    # plot load per household type
    fig, ax = plt.subplots()
    sns.barplot(
        data=df,
        x=type_col,
        y=DFColumnsLoad.TOTAL_DEMAND,
        hue=size_col,  # groups the bars
        estimator="mean",
        # errorbar=None,
        ax=ax,
    )
    ax.set_xlabel("Jährlicher Verbrauch [kWh]")
    ax.set_ylabel("Anzahl Haushalte")
    plt.xticks(rotation=90)
    fig.tight_layout()
    fig.savefig(result_dir / "total_demand_dist_by_hh_type.svg")

    pass


def sum_duration_curve(path: Path, result_dir: Path) -> pd.Series:
    sumcurve = pd.read_csv(path / LoadFiles.SUMPROFILE, parse_dates=[0])
    start_day = sumcurve[DFColumnsLoad.TIME].min().date()
    end_day = sumcurve[DFColumnsLoad.TIME].max().date()
    hours = datetime_to_hours(sumcurve[DFColumnsLoad.TIME])

    # sort by load to get the load duration curve
    sumcurve.sort_values(DFColumnsLoad.TOTAL_LOAD, inplace=True, ascending=False)

    # scale to a suitable unit
    unit, _ = adapt_scaling(sumcurve, DFColumnsLoad.TOTAL_LOAD, "W")

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
    fig.tight_layout()
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


def raster_plot(path: Path, result_dir: Path):
    # load the city sum profile
    df = pd.read_csv(path / LoadFiles.SUMPROFILE, parse_dates=[0], index_col=0)
    unit, _ = adapt_scaling(df, DFColumnsLoad.TOTAL_LOAD, "W")

    # Reshape data to hours × days
    assert isinstance(df.index, pd.DatetimeIndex), "Datetimes not parsed correctly"
    df["day"] = df.index.dayofyear
    df["time"] = df.index.time  # or use hour/minute if finer
    df["hour"] = df.index.hour + df.index.minute / 60

    # Pivot: rows = time, columns = day, values = load
    heatmap_data = df.pivot_table(
        index="hour", columns="day", values=DFColumnsLoad.TOTAL_LOAD
    )

    fig, ax = plt.subplots(figsize=(15, 6), dpi=400)
    im = ax.imshow(heatmap_data, aspect="auto", origin="upper", cmap="viridis")

    # Add colorbar
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(f"Elektrische Last [{unit}]")
    # cbar.set_label("Globalstrahlung [W/m²]")

    # draw major ticks, but label minor ticks to put each label between two major ticks
    date_formatter = mdates.DateFormatter("%b")
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(ticker.NullFormatter())
    ax.xaxis.set_minor_locator(mdates.MonthLocator(bymonthday=16))
    ax.xaxis.set_minor_formatter(date_formatter)
    # remove the minor ticks
    for tick in ax.xaxis.get_minor_ticks():
        tick.tick1line.set_markersize(0)
        tick.tick2line.set_markersize(0)
        tick.label1.set_horizontalalignment("center")

    vals_per_day = len(heatmap_data.index)

    # define y-ticks (time)
    def hour_formatter(x, pos):
        x = x * 24 / vals_per_day
        h = int(x)
        m = int((x - h) * 60)
        return f"{h % 24:02d}:{m:02d}"

    ax.yaxis.set_major_formatter(ticker.FuncFormatter(hour_formatter))
    ax.set_yticks(np.linspace(0, vals_per_day, num=7))

    # Labels and title
    ax.set_xlabel(f"{df.index[0].year}")
    ax.set_ylabel("Uhrzeit")
    fig.tight_layout()
    fig.savefig(result_dir / "raster_city_load.svg", transparent=True, dpi="figure")


def create_load_stat_plots(path: Path, result_dir: Path, instances: str):
    result_dir.mkdir(parents=True, exist_ok=True)
    h25 = sum_duration_curve(path, result_dir)
    stat_curves(path, result_dir, h25, True)
    stat_curves(path, result_dir, h25, False)
    total_demand_distribution(path, result_dir, instances)
    total_demand_distribution_by_hh_type(path, result_dir, instances)
    simultaneity_curves(path, result_dir, instances)


def main(postproc_path: Path, plot_path: Path):
    sns.set_theme()
    hh_data_path = postproc_path / "loads/aggregated_household"
    create_load_stat_plots(hh_data_path, plot_path / "household", "Haushalte")
    house_data_path = postproc_path / "loads/aggregated_house"
    create_load_stat_plots(house_data_path, plot_path / "house", "Häuser")
    raster_plot(house_data_path, plot_path)


if __name__ == "__main__":
    postproc_path = Path("R:/phd_dir/results/scenario_julich_02/Postprocessed")
    plot_path = postproc_path / "plots/loads"
    main(postproc_path, plot_path)
