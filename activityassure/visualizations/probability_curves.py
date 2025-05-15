"""
Plots stacked daily probability curves.
"""

from datetime import datetime, timedelta
import os
import pandas as pd
import seaborn as sns  # type: ignore
import matplotlib.pyplot as plt
import matplotlib.dates


def plot_stacked_probability_curves(name: str, directory: str) -> None:
    csv_path = os.path.join(directory, name + ".csv")
    data = pd.read_csv(csv_path, index_col=0)

    # change capitalization of category names
    data.index = data.index.map(lambda s: s.title())

    print(data)

    # create time values for x axis
    resolution = timedelta(days=1) / len(data.columns)
    print(f"Assuming a resolution of {resolution}")
    start_time = datetime.strptime("04:00", "%H:%M")
    end_time = start_time + timedelta(days=1) - resolution
    time_values = pd.date_range(start_time, end_time, freq=resolution)
    # time_values = [(x/6) % 24 for x in range(0, 145)]

    sns.set_theme()

    fig, ax = plt.subplots(figsize=(5, 6))
    fig.subplots_adjust(left=0.2, top=0.95, bottom=0.5, right=0.95)

    plt.stackplot(time_values, data.values, labels=data.index)

    # change x-tick labels
    hours_fmt = matplotlib.dates.DateFormatter("%#H")
    hours = matplotlib.dates.HourLocator(byhour=range(1, 24, 3))
    ax.xaxis.set_major_locator(hours)
    ax.xaxis.set_major_formatter(hours_fmt)

    # Shrink current axis by 20%
    # box = ax.get_position()
    # ax.set_position([box.x0 * 0.3, box.y0 * 1.5, box.width, box.height * 0.5])

    # place legend below figure
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2))

    plt.xlabel("Time [h]")
    plt.ylabel("Probability")

    plot_dir = os.path.join(directory, "plots")
    os.makedirs(plot_dir, exist_ok=True)
    plot_filename = os.path.join(plot_dir, f"{name}.svg")
    plt.savefig(plot_filename, transparent=True)
    plt.show()


if __name__ == "__main__":
    dir = ".\\data\\validation_data_sets\\activity_validation_data_set\\probability_profiles"
    for name in os.listdir(dir):
        if os.path.isfile(os.path.join(dir, name)):
            # name = "probabilities ('DE', 1, 0.0, 0)"
            name = os.path.splitext(name)[0]
            plot_stacked_probability_curves(name, dir)
