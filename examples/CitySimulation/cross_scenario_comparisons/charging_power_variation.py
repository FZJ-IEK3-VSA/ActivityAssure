"""Comparisons and assessments across multiple result data sets"""

import logging
from pathlib import Path

from matplotlib import pyplot as plt
import pandas as pd
import seaborn as sns

from load_profile_analysis import datetime_to_hours
from load_profile_analysis import adapt_scaling
from paths import DFColumnsLoad, LoadFiles, SubDirs


def charging_power_comparison_sumprofiles(base_results: Path, output: Path):
    subdir = f"{SubDirs.POSTPROCESSED_DIR}/loads/aggregated_household"
    path3kW = base_results / "scenario_julich_100_3kW" / subdir
    path11kW = base_results / "scenario_julich_100_11kW" / subdir
    data3kW = pd.read_csv(path3kW / LoadFiles.SUMPROFILE, parse_dates=[0])
    data11kW = pd.read_csv(path11kW / LoadFiles.SUMPROFILE, parse_dates=[0])

    unit3 = adapt_scaling(data3kW, DFColumnsLoad.TOTAL_LOAD)
    unit11 = adapt_scaling(data11kW, DFColumnsLoad.TOTAL_LOAD)
    assert unit3 == unit11, "Different value ranges"

    assert (data3kW["Time"] == data11kW["Time"]).all(), "Incompatible time axes"
    hours = datetime_to_hours(data3kW["Time"])

    data3kW.sort_values(DFColumnsLoad.TOTAL_LOAD, inplace=True, ascending=False)
    data11kW.sort_values(DFColumnsLoad.TOTAL_LOAD, inplace=True, ascending=False)
    data3kW.reset_index(drop=True, inplace=True)
    data11kW.reset_index(drop=True, inplace=True)

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    txt = "kW Ladestationen"
    sns.lineplot(data3kW, y=DFColumnsLoad.TOTAL_LOAD, x=hours, ax=ax, label=f"3 {txt}")
    sns.lineplot(
        data11kW, y=DFColumnsLoad.TOTAL_LOAD, x=hours, ax=ax, label=f"11 {txt}"
    )
    ax.xaxis.set_label_text("Dauer [h]")
    ax.yaxis.set_label_text(f"Elektrische Last [{unit3}]")
    fig.savefig(output / "sum_duration.svg")

    max3 = float(data3kW[DFColumnsLoad.TOTAL_LOAD].max())
    max11 = float(data11kW[DFColumnsLoad.TOTAL_LOAD].max())
    logging.info(
        f"Sum curve maximums:\n3 kW: {max3} {unit3}\n11 kW: "
        f"{max11} {unit3}\nDifference: {max11 - max3} {unit3}"
    )


def charging_power_comparison_maxloads(base_results: Path, output: Path):
    subdir = f"{SubDirs.POSTPROCESSED_DIR}/loads/aggregated_household"
    path3kW = base_results / "scenario_julich_100_3kW" / subdir
    path11kW = base_results / "scenario_julich_100_11kW" / subdir
    data3kW = pd.read_csv(path3kW / LoadFiles.STATS, parse_dates=[0])
    data11kW = pd.read_csv(path11kW / LoadFiles.STATS, parse_dates=[0])

    assert (data3kW["Time"] == data11kW["Time"]).all(), "Incompatible time axes"
    hours = datetime_to_hours(data3kW["Time"])

    data3kW.sort_values("max", inplace=True, ascending=False)
    data11kW.sort_values("max", inplace=True, ascending=False)
    data3kW.reset_index(drop=True, inplace=True)
    data11kW.reset_index(drop=True, inplace=True)

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    txt = "kW Ladestationen"
    sns.lineplot(data3kW, y="max", x=hours, ax=ax, label=f"3 {txt}")
    sns.lineplot(data11kW, y="max", x=hours, ax=ax, label=f"11 {txt}")
    ax.xaxis.set_label_text("Dauer [h]")
    ax.yaxis.set_label_text("Elektrische Spitzenlast [W]")
    fig.savefig(output / "peak_duration.svg")


def charging_power_comparison_total_demand(base_results: Path, output: Path):
    subdir = f"{SubDirs.POSTPROCESSED_DIR}/loads/aggregated_household"
    path3kW = base_results / "scenario_julich_100_3kW" / subdir
    path11kW = base_results / "scenario_julich_100_11kW" / subdir
    data3kW = pd.read_csv(path3kW / LoadFiles.TOTALS)
    data11kW = pd.read_csv(path11kW / LoadFiles.TOTALS)

    data3kW.sort_values(DFColumnsLoad.TOTAL_DEMAND, inplace=True, ascending=False)
    data11kW.sort_values(DFColumnsLoad.TOTAL_DEMAND, inplace=True, ascending=False)
    data3kW.reset_index(drop=True, inplace=True)
    data11kW.reset_index(drop=True, inplace=True)
    assert len(data3kW) == len(data11kW), "Different lengths"
    hh_numbers = range(len(data3kW))

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)

    txt = "kW Ladestationen"
    sns.lineplot(
        data3kW, ax=ax, y=DFColumnsLoad.TOTAL_DEMAND, x=hh_numbers, label=f"3 {txt}"
    )
    sns.lineplot(
        data11kW, ax=ax, y=DFColumnsLoad.TOTAL_DEMAND, x=hh_numbers, label=f"11 {txt}"
    )
    # add a second axis for the average load
    ax2 = ax.twinx()
    sns.lineplot(
        data3kW,
        ax=ax2,  # type: ignore
        y=DFColumnsLoad.AVERAGE_LOAD,
        x=hh_numbers,
    )
    ax.xaxis.set_label_text("Haushalte")
    ax.yaxis.set_label_text("Stromverbrauch [kWh]")
    ax2.yaxis.set_label_text("Durchschnittliche Last [W]")
    fig.savefig(output / "total_demands.svg")


def charging_power_comparison(base_results: Path, output: Path):
    logging.info("--- charging power scenarios (3 kW vs. 11 kW) ---")
    charge_output = output / "charging_power_3kW_vs_11kW"
    charge_output.mkdir(parents=True, exist_ok=True)
    charging_power_comparison_sumprofiles(base_results, charge_output)
    charging_power_comparison_maxloads(base_results, charge_output)
    charging_power_comparison_total_demand(base_results, charge_output)


def main():
    #: directory that contains all individual result directories
    base_results = Path("R:/phd_dir/results")
    output = base_results / "comparisons"
    output.mkdir(parents=True, exist_ok=True)
    sns.set_theme()  # default theme
    charging_power_comparison(base_results, output)


if __name__ == "__main__":
    # init logging
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    main()
