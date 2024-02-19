import os
from typing import Any
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np

from activity_validator.hetus_data_processing import hetus_constants


def plot_heatmap_diary(data: pd.DataFrame, tick_labels, name):
    # create the heatmap
    fig, ax = plt.subplots(figsize=(7, 5))
    fig.subplots_adjust(left=0.35)
    heatmap: plt.Axes = sns.heatmap(
        data,
        linewidths=0.5,
        square=True,
        cmap="RdYlGn",
        norm=LogNorm(vmin=10, vmax=10e2),
        cbar_kws={"label": "Number of Diary Entries", "shrink": 0.75},
    )
    # heatmap.set_facecolor("black")
    # plt.xticks(rotation=0)

    heatmap.set_yticks(np.arange(0.5, len(data.index)), tick_labels)
    plt.tick_params(axis="y", which="both", length=0)
    plt.tick_params(axis="x", which="both", length=0)

    heatmap.set_ylabel("")
    heatmap.set_xlabel("Country")
    # heatmap.set_title("Number of Diary Entries")

    plt.savefig(os.path.join(dir, f"{name}.svg"), transparent=True)
    plt.show()


def plot_heatmaps_diary_filtered_and_unfiltered(name: str, dir: str):
    # load data
    path = os.path.join(dir, name + ".csv")
    data = pd.read_csv(path, header=[0], index_col=[0, 1, 2])

    # rearrange index levels to keep categories for male and female next to each other
    data = data.reorder_levels([2, 1, 0])
    data.sort_index(level=[0, 1], inplace=True)
    print(data.head())

    # create hierarchical tick labels
    tick_labels: list[tuple] = [data.index[0]]
    for i in range(1, len(data.index)):
        a, b, c = data.index[i]
        l: tuple = (c,)
        if data.index[i - 1][0] != a:
            l = a, b, c
        elif data.index[i - 1][1] != b:
            l = b, c
        tick_labels.append(l)
    tick_labels_str = [
        " - ".join([str(y).replace("_", " ") for y in x]) for x in tick_labels
    ]
    # tick_labels = [f"{a:>11} {b:>8} {c:>6}" for a,b,c in data.index] # does not work due to proportional font

    # plot the unfiltered data
    plot_heatmap_diary(data, tick_labels_str, name)

    total = len(data) * len(data.columns)
    zeros = (data == 0).sum().sum()
    nans = data.isna().sum().sum()
    no_data = zeros + nans

    # filter categories that are too small
    data[data <= hetus_constants.MIN_CELL_SIZE] = 0

    filtered_out = (data == 0).sum().sum() - zeros
    print("--- Category Data Availability ---")
    print(f"There was no data available for {no_data} categories.")
    print(f"Additionally, {filtered_out} categories were too small and filtered out.")
    print(
        f"All in all, data is available for {total - no_data - filtered_out} of {total} categories."
    )

    # plot the filtered heatmap as well
    plot_heatmap_diary(data, tick_labels_str, f"{name}_filtered")


def plot_heatmap_person(name: str, dir: str):
    # load data
    path = os.path.join(dir, name + ".csv")
    data = pd.read_csv(path, header=[0], index_col=[0, 1])

    # rearrange index levels to keep categories for male and female next to each other
    data = data.reorder_levels([1, 0])
    data.sort_index(level=[0, 1], inplace=True)
    print(data.head())

    # create the heatmap
    fig, ax = plt.subplots(figsize=(7, 3))
    fig.subplots_adjust(left=0.3)
    heatmap: plt.Axes = sns.heatmap(
        data,
        linewidths=0.5,
        square=True,
        cmap="RdYlGn",
        norm=LogNorm(vmin=10, vmax=10e2),
        cbar_kws={"label": "Number of Persons", "shrink": 0.85},
    )
    # heatmap.set_facecolor("black")
    # plt.xticks(rotation=0)

    # create hierarchical tick labels
    # Remark: the following link might help to create actual hierarchical tick labels
    # https://stackoverflow.com/questions/71048752/adding-multi-level-x-axis
    tick_labels: list[tuple[Any]] = [data.index[0]]
    for i in range(1, len(data.index)):
        a, b = data.index[i]
        l = (b,)
        if data.index[i - 1][0] != a:
            l = a, b
        # elif data.index[i-1][1] != b:
        #     l = b,c
        tick_labels.append(l)
    tick_labels = [" - ".join([y.replace("_", " ") for y in x]) for x in tick_labels]
    # tick_labels = [f"{a:>11} {b:>8} {c:>6}" for a,b,c in data.index] # does not work due to proportional font

    heatmap.set_yticks(np.arange(0.5, len(data.index)), tick_labels)
    plt.tick_params(axis="y", which="both", length=0)
    plt.tick_params(axis="x", which="both", length=0)

    heatmap.set_ylabel("")
    heatmap.set_xlabel("Country")
    # heatmap.set_title("Number of Diary Entries")

    plt.savefig(os.path.join(dir, f"{name}.svg"), transparent=True)
    plt.show()


if __name__ == "__main__":
    dir = ".\\data\\validation data sets\\latest\\categories"
    name = "category_sizes"
    plot_heatmaps_diary_filtered_and_unfiltered(name, dir)
