from datetime import timedelta
from pathlib import Path
from matplotlib import pyplot as plt
import pandas as pd


def plot_distribution(data: list, path: Path):
    fig, ax = plt.subplots()
    d = pd.Series(data)
    _ = d.plot.hist(bins=50)

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)


def plot_distribution_td(data: list[timedelta], path: Path):
    minutes = [d.total_seconds() / 60 for d in data]
    plot_distribution(minutes, path)
