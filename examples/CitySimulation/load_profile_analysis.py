"""Plots for analyzing load profiles of a city simulation"""

from pathlib import Path
from matplotlib import pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import pandas as pd

from load_profile_processing import Files


def stat_curves(path, result_dir):
    statpath = path / Files.MEANDAY_STATS
    stats = pd.read_csv(statpath, parse_dates=[0], index_col=0)
    # stats = stats.iloc[:1440, :]
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    for stat in stats.columns:
        # if stat == "max":
        #     continue
        ax.plot(stats[stat], label=stat)

    # add axis labels
    hours = mdates.HourLocator(byhour=range(0, 24, 3))
    hours_fmt = mdates.DateFormatter("%#H")
    ax.xaxis.set_major_locator(hours)
    ax.xaxis.set_major_formatter(hours_fmt)
    ax.xaxis.set_label_text("Uhrzeit [h]")
    ax.yaxis.set_label_text("Elektrische Last [kWh]")
    ax.legend()
    fig.savefig(result_dir / "mean_day_stats.svg")


def total_load_distribution(path: Path, result_dir: Path):
    totals = pd.read_csv(path / Files.TOTALS)
    totals.sort_values("Load [kWh]", inplace=True, ascending=False)

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)

    sns.lineplot(totals, ax=ax, y="Load [kWh]", x=range(len(totals)))
    ax.set_xticklabels([])
    ax.xaxis.set_label_text("Häuser")
    ax.yaxis.set_label_text("Elektrische Last [kWh]")
    fig.savefig(result_dir / "total_per_house.svg")


def city_duration_curve(path: Path, result_dir: Path):
    totals = pd.read_csv(path / Files.CITYSUM)
    totals.sort_values("Load [kWh]", inplace=True, ascending=False)

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)

    sns.lineplot(totals, ax=ax, y="Load [kWh]", x=range(len(totals)))
    ax.xaxis.set_label_text("Dauer [min]")
    ax.yaxis.set_label_text("Elektrische Last [kWh]")
    fig.savefig(result_dir / "city_duration_curve.svg")


def population_statistics(path: Path, result_dir: Path):
    # TODO: read json files and build dataframe from that instead
    path = Path(
        r"R:\repos\activityassure\data\city\postprocessed\scenario_city-julich_25\population_stats.csv"
    )
    stats = pd.read_csv(path)

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    df_long = stats.melt(id_vars="measure", var_name="Dataset", value_name="Value")

    sns.barplot(x="measure", ax=ax, y="Value", hue="Dataset", data=df_long)
    fig.savefig(result_dir / "city_duration_curve.svg")
    plt.show()


def create_plots(path: Path, result_dir: Path):
    result_dir.mkdir(parents=True, exist_ok=True)
    # stat_curves(path, result_dir)
    # total_load_distribution(path, result_dir)
    # city_duration_curve(path, result_dir)
    population_statistics(path, result_dir)


def main():
    plot_path = Path("data/city/results/load")
    postproc_path = Path(
        "R:/repos/activityassure/data/city/postprocessed/scenario_city-julich_25"
    )
    create_plots(postproc_path, plot_path)


if __name__ == "__main__":
    main()
