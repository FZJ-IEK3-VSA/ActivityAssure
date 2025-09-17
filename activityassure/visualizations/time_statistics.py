from pathlib import Path
from matplotlib import pyplot as plt
import matplotlib.patheffects as path_effects
from matplotlib import container as mplcontainer
import pandas as pd

from activityassure.profile_category import ProfileCategory
from activityassure.validation_statistics import ValidationSet, ValidationStatistics
from activityassure.visualizations import time_statistics
from activityassure.visualizations.utils import (
    CM_TO_INCH,
    LABEL_DICT,
    replace_substrings,
)


def profile_sorting_key(key: tuple[str, ProfileCategory]) -> str:
    """Helper function to convert a profile category to a string for sorting"""
    name, category = key
    category_parts = str(category).split("_", 1)
    if len(category_parts) == 1:
        return category_parts[0]
    return category_parts[1] + "_" + category_parts[0]


def convert_key_to_label(key: tuple[str, ProfileCategory]) -> str:
    name, category = key
    category_str = replace_substrings(str(category), LABEL_DICT).replace("_", " ")
    name_prefix = (f"{name} ") if name else ""
    return name_prefix + category_str


def plot_total_time_spent(
    statistics_country_1: dict[ProfileCategory, ValidationStatistics],
    statistics_country_2: dict[ProfileCategory, ValidationStatistics],
    plot_filepath: Path,
    names: list[str] = [],
):
    """Creates a stacked bar chart comparing total time spent per activity, for
    the two passed sets of statistics. Aggregates less important activities into
    the group 'minor activities'.

    :param statistics_country_1: first set of statistics
    :param statistics_country_2: second set of statistics
    :param plot_path: result filepath for the bar chart
    :param names: optional names to identify the data sets in the plot, defaults to []
    """
    time_activity_distribution: dict[tuple[str, ProfileCategory], pd.Series[float]] = {}
    statistics = [statistics_country_1, statistics_country_2]
    for i, statistic in enumerate(statistics):
        name = names[i] if names else ""
        for k, v in statistic.items():
            time_activity_distribution[(name, k)] = (
                v.probability_profiles.mean(axis=1) * 24
            )

    num_profiles = len(time_activity_distribution)

    plot_height = (4 + 0.5 * num_profiles) * CM_TO_INCH
    fig, ax = plt.subplots(figsize=(16 * CM_TO_INCH, plot_height))
    combined_df = pd.DataFrame(time_activity_distribution)

    # sort by total activity share
    combined_df["total_shares"] = combined_df.mean(axis="columns")
    sorted_df = combined_df.sort_values("total_shares", ascending=False)  # type: ignore

    # combine all activities with a low overall share and include the activity "other"
    min_share = 0.05 * 24
    condition = (sorted_df["total_shares"] < min_share) | (sorted_df.index == "other")
    minor_activities = sorted_df[condition].sum()
    minor_activities.name = "minor activities"
    sorted_df = pd.concat([sorted_df[~condition], minor_activities.to_frame().T])
    sorted_df.drop(columns="total_shares", inplace=True)

    # sort by profile category
    sorted_cols = sorted(sorted_df.columns, key=profile_sorting_key)  # type: ignore
    df_to_plot = sorted_df[sorted_cols].T

    # set suitable label texts
    label_texts = [convert_key_to_label(k) for k in df_to_plot.index]
    df_to_plot.index = label_texts
    df_to_plot.plot(kind="barh", stacked=True, ax=ax, width=0.8)

    # add labels to the bars
    for i, c in enumerate(ax.containers):
        # if the segment is small, don't add a label
        labels = [round(v, 1) if v > 1 else "" for v in df_to_plot.iloc[:, i]]

        # remove the labels parameter if it's not needed for customized labels
        assert isinstance(c, mplcontainer.BarContainer)
        texts = ax.bar_label(c, labels=labels, label_type="center")  # , color="white")

        # add a white stroke to the text for better readability
        for text in texts:
            text.set_path_effects(
                [
                    path_effects.Stroke(linewidth=1, foreground="white"),
                    path_effects.Normal(),
                ]
            )

    ax.set_xlabel("time [h]")
    ax.legend(loc="lower right", bbox_to_anchor=(1, 1), ncol=3)
    ax.set_xlim(0, 24)
    fig.tight_layout()
    plot_filepath.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(plot_filepath)


def plot_total_time_bar_chart_countries(
    validation_data_path: Path,
    countries: list[str],
    output_path: Path,
):
    """Creates a stacked bar chart comparing total time
    spent per activity across different countries.

    :param validation_data_path: TUS statistics path
    :param countries: the countries to compare
    :param output_path: result path for the bar chart
    """
    # load LPG statistics and validation statistics
    datasets = [
        ValidationSet.load(validation_data_path, country=country)
        for country in countries
    ]
    validation_data1 = datasets[0]
    validation_data2 = datasets[1]

    # Plot total time spent
    time_statistics.plot_total_time_spent(
        validation_data1.statistics,
        validation_data2.statistics,
        output_path,
    )


def plot_total_time_bar_chart(
    data_path1: Path,
    data_path2: Path,
    data_set_names: list[str],
    output_path: Path,
):
    """Creates a stacked bar chart comparing total time
    spent per activity across two datasets.

    :param data_path1: the first data set
    :param data_path2: the second data set
    :param data_set_names: names of the datasets in order
    :param output_path: result path for the bar chart
    """
    data1 = ValidationSet.load(data_path1)
    data2 = ValidationSet.load(data_path2)

    ValidationSet.drop_unmatched_categories(data1, data2)

    # Plot total time spent
    time_statistics.plot_total_time_spent(
        data1.statistics, data2.statistics, output_path, data_set_names
    )
