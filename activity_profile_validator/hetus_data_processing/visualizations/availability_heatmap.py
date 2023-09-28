import os
from typing import Any, List, Tuple
import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np


def plot_heatmap_diary(name: str, dir: str):
    # load data
    path = os.path.join(dir, name + ".csv")
    data = pd.read_csv(path, header=[0], index_col=[0, 1, 2])

    # rearrange index levels to keep categories for male and female next to each other
    data = data.reorder_levels([2,1,0])
    data.sort_index(level=[0,1], inplace=True)
    print(data.head())

    # create the heatmap
    fig, ax = plt.subplots(figsize=(7, 5))
    fig.subplots_adjust(left=0.3)
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

    # create hierarchical tick labels
    tick_labels: List[Tuple[Any]] = [data.index[0]]
    for i in range(1, len(data.index)):
        a,b,c = data.index[i]
        l = (c,)
        if data.index[i-1][0] != a:
            l = a,b,c
        elif data.index[i-1][1] != b:
            l = b,c
        tick_labels.append(l)
    tick_labels = [" - ".join([str(y).replace("_", " ") for y in x]) for x in tick_labels]
    # tick_labels = [f"{a:>11} {b:>8} {c:>6}" for a,b,c in data.index] # does not work due to proportional font

    heatmap.set_yticks(np.arange(0.5, len(data.index)), tick_labels)
    plt.tick_params(axis='y', which='both', length=0)
    plt.tick_params(axis='x', which='both', length=0)

    heatmap.set_ylabel("")
    heatmap.set_xlabel("Country")
    # heatmap.set_title("Number of Diary Entries")

    plt.savefig(os.path.join(dir, f"{name}.svg"), transparent=True)
    plt.show()


def plot_heatmap_person(name: str, dir: str):
    # load data
    path = os.path.join(dir, name + ".csv")
    data = pd.read_csv(path, header=[0], index_col=[0, 1])

    # rearrange index levels to keep categories for male and female next to each other
    data = data.reorder_levels([1,0])
    data.sort_index(level=[0,1], inplace=True)
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
    tick_labels: List[Tuple[Any]] = [data.index[0]]
    for i in range(1, len(data.index)):
        a,b = data.index[i]
        l = (b,)
        if data.index[i-1][0] != a:
            l = a,b
        # elif data.index[i-1][1] != b:
        #     l = b,c
        tick_labels.append(l)
    tick_labels = [" - ".join([y.replace("_", " ") for y in x]) for x in tick_labels]
    # tick_labels = [f"{a:>11} {b:>8} {c:>6}" for a,b,c in data.index] # does not work due to proportional font

    heatmap.set_yticks(np.arange(0.5, len(data.index)), tick_labels)
    plt.tick_params(axis='y', which='both', length=0)
    plt.tick_params(axis='x', which='both', length=0)

    heatmap.set_ylabel("")
    heatmap.set_xlabel("Country")
    # heatmap.set_title("Number of Diary Entries")

    plt.savefig(os.path.join(dir, f"{name}.svg"), transparent=True)
    plt.show()


if __name__ == "__main__":
    dir = ".\\data\\validation\\categories"
    name = "cat_COUNTRY_INC1_Work Status_Day Type"
    plot_heatmap_diary(name, dir)
