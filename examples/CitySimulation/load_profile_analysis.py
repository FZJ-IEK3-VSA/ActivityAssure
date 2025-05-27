"""Plots for analyzing load profiles of a city simulation"""

from datetime import date
from pathlib import Path
from matplotlib import pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import seaborn as sns
import pandas as pd

from activityassure.loadprofiles.bdew_slp import BDEWProfileProvider
from paths import DFColumns, LoadFiles


def stat_curves(path, result_dir):
    statpath = path / LoadFiles.MEANDAY_STATS
    stats = pd.read_csv(statpath, index_col=0, parse_dates=[0], date_format="%H:%M:%S")
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    for stat in stats.columns:
        # if stat == "max":
        #     continue
        ax.plot(stats[stat], label=stat)

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


def sum_duration_curve(path: Path, result_dir: Path):
    sumcurve = pd.read_csv(path / LoadFiles.SUMPROFILE, parse_dates=[0])
    start_day = sumcurve[DFColumns.TIME].min().date()
    end_day = sumcurve[DFColumns.TIME].max().date()

    # sort by load to get the load duration curve
    sumcurve.sort_values(DFColumns.LOAD, inplace=True, ascending=False)

    # create H25 standard profile load duration curve
    bdewprovider = BDEWProfileProvider()
    h25 = bdewprovider.get_profile_for_date_range(start_day, end_day)
    h25.sort_values(inplace=True, ascending=False)

    # scale H25 to the same total demand
    factor = sumcurve[DFColumns.LOAD].sum() / h25.sum()
    # adjust to different resolutions so the curves can be compared
    factor *= len(h25) / len(sumcurve)
    h25 *= factor

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)

    sns.lineplot(sumcurve, ax=ax, y=DFColumns.LOAD, x=range(len(sumcurve)))
    sns.lineplot(
        y=h25,
        ax=ax,
        label="H25 Standardprofil",
        x=np.linspace(0, len(sumcurve), len(h25)),
    )
    ax.xaxis.set_label_text("Dauer [min]")  # TODO: not correct for 600s HH data
    ax.yaxis.set_label_text("Elektrische Last [kWh]")
    fig.savefig(result_dir / "sum_duration_curve.svg")


def create_load_stat_plots(path: Path, result_dir: Path):
    result_dir.mkdir(parents=True, exist_ok=True)
    stat_curves(path, result_dir)
    total_load_distribution(path, result_dir)
    sum_duration_curve(path, result_dir)


def main(postproc_path: Path, plot_path: Path):
    hh_data_path = postproc_path / "loads/aggregated_household"
    create_load_stat_plots(hh_data_path, plot_path / "household")
    house_data_path = postproc_path / "loads/aggregated_house"
    create_load_stat_plots(house_data_path, plot_path / "house")


if __name__ == "__main__":
    postproc_path = Path("D:/LPG/Results/scenario_julich-grosse-rurstr/Postprocessed")
    plot_path = postproc_path / "plots"
    main(postproc_path, plot_path)
