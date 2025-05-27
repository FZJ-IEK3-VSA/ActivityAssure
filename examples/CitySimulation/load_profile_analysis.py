"""Plots for analyzing load profiles of a city simulation"""

from pathlib import Path
from matplotlib import pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import pandas as pd

from paths import LoadFiles


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
    totals.sort_values("Load [kWh]", inplace=True, ascending=False)

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)

    sns.lineplot(totals, ax=ax, y="Load [kWh]", x=range(len(totals)))
    ax.set_xticklabels([])
    ax.xaxis.set_label_text("Häuser")
    ax.yaxis.set_label_text("Elektrische Last [kWh]")
    fig.savefig(result_dir / "profile_sums.svg")


def sum_duration_curve(path: Path, result_dir: Path):
    totals = pd.read_csv(path / LoadFiles.SUMPROFILE)
    totals.sort_values("Load [kWh]", inplace=True, ascending=False)

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)

    sns.lineplot(totals, ax=ax, y="Load [kWh]", x=range(len(totals)))
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
