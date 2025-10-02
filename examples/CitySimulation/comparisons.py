"""Comparisons and assessments across multiple result data sets"""

from pathlib import Path

from matplotlib import pyplot as plt
import pandas as pd
import seaborn as sns

from load_profile_analysis import datetime_to_hours
from load_profile_analysis import adapt_scaling
from paths import DFColumnsLoad, LoadFiles, SubDirs

#: directory that contains all individual result directories
RESULTS_PATH = Path("R:/phd_dir/results")
OUTPUT = RESULTS_PATH / "comparisons"


def charging_station_comparions():
    subdir = f"{SubDirs.POSTPROCESSED_DIR}/loads/aggregated_household"
    path3kW = RESULTS_PATH / "scenario_julich_100_3kW" / subdir
    path11kW = RESULTS_PATH / "scenario_julich_100_11kW" / subdir
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
    plt.show()
    fig.savefig(OUTPUT / "sum_duration_3kW_vs_11kW.svg")


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    charging_station_comparions()


if __name__ == "__main__":
    main()
