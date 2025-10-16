"""Comparisons and assessments across multiple result data sets"""

import logging
from pathlib import Path
import sys

from matplotlib import pyplot as plt
import pandas as pd
import seaborn as sns

# add path to CitySimulation example directory
sys.path.append(str(Path(__file__).resolve().parents[1]))

from load_profile_analysis import datetime_to_hours, adapt_scaling
from paths import DFColumnsLoad, LoadFiles, SubDirs

scenario_name_3kW = "scenario_julich_02_3kW"
scenario_name_11kW = "scenario_julich_02"


def charging_power_comparison_sumprofiles(base_results: Path, output: Path):
    subdir = f"{SubDirs.POSTPROCESSED_DIR}/loads/aggregated_household"
    path3kW = base_results / scenario_name_3kW / subdir
    path11kW = base_results / scenario_name_11kW / subdir
    data3kW = pd.read_csv(path3kW / LoadFiles.SUMPROFILE, parse_dates=[0])
    data11kW = pd.read_csv(path11kW / LoadFiles.SUMPROFILE, parse_dates=[0])

    unit3, factor = adapt_scaling(data3kW, DFColumnsLoad.TOTAL_LOAD)
    unit11, _ = adapt_scaling(data11kW, DFColumnsLoad.TOTAL_LOAD)
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
    sns.lineplot(
        data11kW, y=DFColumnsLoad.TOTAL_LOAD, x=hours, ax=ax, label=f"11 {txt}"
    )
    sns.lineplot(data3kW, y=DFColumnsLoad.TOTAL_LOAD, x=hours, ax=ax, label=f"3 {txt}")
    ax.xaxis.set_label_text("Dauer [h]")
    ax.yaxis.set_label_text(f"Elektrische Last [{unit3}]")
    fig.savefig(output / "sum_duration.svg")

    # define charging powers in the scenarios
    CHARGE3 = 3000 / factor
    CHARGE11 = 11000 / factor

    logging.info(
        "Comparing minimum and maximum of both sum curves. In theory, the 11kW sum "
        "curve should have a higher maximum when many people charge at the same time. "
        "Conversely, for sufficiently large scenarios it should have a lower minimum "
        "when almost no charging is happening, as there will always be some charging "
        "with 3kW"
    )
    min3 = float(data3kW[DFColumnsLoad.TOTAL_LOAD].max())
    min11 = float(data11kW[DFColumnsLoad.TOTAL_LOAD].max())
    logging.info(
        f"Sum curve minimums:\n3 kW: {min3:.3f} {unit3}\n11 kW: "
        f"{min11:.3f} {unit3}\nDifference: {min3 - min11:.3f} {unit3}"
        f"That's {(min3 - min11) / CHARGE3:.1f} 3kW charging stations"
    )
    max3 = float(data3kW[DFColumnsLoad.TOTAL_LOAD].max())
    max11 = float(data11kW[DFColumnsLoad.TOTAL_LOAD].max())
    logging.info(
        f"Sum curve maximums:\n3 kW: {max3:.3f} {unit3}\n11 kW: "
        f"{max11:.3f} {unit3}\nDifference: {max11 - max3:.3f} {unit3}"
        f"That's {(max11-max3) / CHARGE11:.1f} 11kW charging stations"
    )


def charging_power_comparison_maxloads(base_results: Path, output: Path):
    subdir = f"{SubDirs.POSTPROCESSED_DIR}/loads/aggregated_household"
    path3kW = base_results / scenario_name_3kW / subdir
    path11kW = base_results / scenario_name_11kW / subdir
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
    path3kW = base_results / scenario_name_3kW / subdir
    path11kW = base_results / scenario_name_11kW / subdir
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
    fig.tight_layout()
    fig.savefig(output / "total_demands.svg")


def car_state_comparison(base_results: Path, output: Path):
    """Plot the different number of charging cars and the resulting
    total charging load for the whole city as simple line plots.

    :param base_results: base directory for city simulation results
    :param output: output directory for plots
    """
    # use the special simulations with additional transport output files
    scenario_name_3kW = "scenario_julich_02_3kW_transport"
    scenario_name_11kW = "scenario_julich_02_transport"
    # read the car state files
    rel_filepath = f"{SubDirs.POSTPROCESSED_DIR}/transport/car_state_counts.csv"
    path3kW = base_results / scenario_name_3kW / rel_filepath
    path11kW = base_results / scenario_name_11kW / rel_filepath
    data3kW = pd.read_csv(path3kW).fillna(0)
    data11kW = pd.read_csv(path11kW).fillna(0)

    charging_col = "ParkingAndCharging"

    # add columns for the plot label and for the actual load values
    label = "Charging Power"
    data3kW[label] = "3 kW"
    data11kW[label] = "11 kW"
    power_in_kw = "Power [kW]"
    data3kW[power_in_kw] = 3
    data11kW[power_in_kw] = 11
    joined = pd.concat([data3kW, data11kW], ignore_index=True)
    total_power_col = "Total Charging Power"
    joined[total_power_col] = joined[charging_col] * joined[power_in_kw]

    # log info about total load
    logging.info("Total charging powers:")
    logging.info(f"3 kW: {joined[joined[label] == "3 kW"][total_power_col].mean()}")
    logging.info(f"11 kW: {joined[joined[label] == "11 kW"][total_power_col].mean()}")

    # plot number of charging cars
    fig, ax = plt.subplots(1, 1)
    sns.lineplot(data=joined, x="Timestep", y=charging_col, hue=label, ax=ax)
    fig.tight_layout()
    fig.savefig(output / "charging_car_number.svg")
    # plot total charging power
    fig, ax = plt.subplots(1, 1)
    sns.lineplot(data=joined, x="Timestep", y=total_power_col, hue=label, ax=ax)
    fig.tight_layout()
    fig.savefig(output / "total_charging_power.svg")


def charging_power_comparison(base_results: Path, output: Path):
    logging.info("--- charging power scenarios (3 kW vs. 11 kW) ---")
    charge_output = output / "charging_power_3kW_vs_11kW"
    charge_output.mkdir(parents=True, exist_ok=True)
    charging_power_comparison_sumprofiles(base_results, charge_output)
    charging_power_comparison_maxloads(base_results, charge_output)
    charging_power_comparison_total_demand(base_results, charge_output)
    car_state_comparison(base_results, charge_output)


def main():
    #: directory that contains all individual result directories
    base_results = Path("R:/phd_dir/results")
    output = base_results / "comparisons"
    output.mkdir(parents=True, exist_ok=True)
    # sns.set_theme()  # default theme
    charging_power_comparison(base_results, output)


if __name__ == "__main__":
    # init logging
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    main()
