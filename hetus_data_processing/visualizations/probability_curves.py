"""
Plots probability profiles for activity groups
"""

from datetime import datetime, time, timedelta
import os
from typing import Any, List, Tuple
import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np


def plot_stacked_probability_curves(name: str, dir: str) -> None:
    path = os.path.join(dir, name+".csv")
    data = pd.read_csv(path, index_col=0)

    data = data.transpose()
    start_time = datetime.strptime('00:00', '%H:%M')
    end_time = datetime.strptime('23:50', '%H:%M')
    index = pd.date_range(start_time, end_time, freq=timedelta(minutes=10)).time
    index = pd.RangeIndex(1, 145)  # TODO: try other time formats?
    assert len(index) == len(data.index)
    data.index = index  # type: ignore
    print(data)

    sns.set_theme()
    
    fig, ax = plt.subplots(figsize=(8, 3))
    fig.subplots_adjust(left=0.3)

    plt.stackplot(data.index, data.values.transpose(), labels=data.columns)
    
    # Shrink current axis by 20%
    box = ax.get_position()
    ax.set_position([box.x0 * 0.3, box.y0 * 1.5, box.width * 0.8, box.height * 0.9])
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))


    plt.xlabel("10 min Timestep")
    plt.ylabel("Probability")

    plt.savefig(os.path.join(dir, f"probability_{name}.png"), transparent=True)
    plt.show()


if __name__ == "__main__":
    dir = ".\\data\\probability_profiles"
    name = "probabilities ('DE', 1, 0.0, 0)"
    plot_stacked_probability_curves(name, dir)
