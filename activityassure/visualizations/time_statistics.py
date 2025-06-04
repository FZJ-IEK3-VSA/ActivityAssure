from pathlib import Path
from activityassure.profile_category import ProfileCategory
from activityassure.validation_statistics import ValidationStatistics
from activityassure.visualizations.utils import (
    CM_TO_INCH,
    LABEL_DICT,
    replace_substrings,
)
from matplotlib import pyplot as plt
import pandas as pd


def profile_sorting_key(category: ProfileCategory) -> str:
    """Helper function to convert a profile category to a string for sorting"""
    category_parts = str(category).split("_", 1)
    if len(category_parts) == 1:
        return category_parts[0]
    return category_parts[1] + "_" + category_parts[0]


def plot_total_time_spent(
    statistics_country_1: dict[ProfileCategory, ValidationStatistics],
    statistics_country_2: dict[ProfileCategory, ValidationStatistics],
    plot_path: Path,
):
    time_activity_distribution = {}
    for _, v in (statistics_country_1 | statistics_country_2).items():
        time_activity_distribution[v.profile_type] = (
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
    summed = sorted_df[condition].sum()
    summed.name = "minor activities"

    sorted_df = pd.concat([sorted_df[~condition], summed.to_frame().T])
    sorted_df.drop(columns="total_shares", inplace=True)
    sorted_cols = sorted(sorted_df.columns, key=profile_sorting_key)  # type: ignore
    df_to_plot = sorted_df[sorted_cols].T
    df_to_plot.plot(kind="barh", stacked=True, ax=ax, width=0.8)

    # add labels to the bars
    for i, c in enumerate(ax.containers):
        # if the segment is small, don't add a label
        labels = [round(v, 1) if v > 1 else "" for v in df_to_plot.iloc[:, i]]

        # remove the labels parameter if it's not needed for customized labels
        ax.bar_label(c, labels=labels, label_type="center")

    # assign
    ax.set_yticklabels(
        [
            replace_substrings(label.get_text(), LABEL_DICT).replace("_", " ")
            for label in ax.get_yticklabels()
        ]
    )

    ax.set_xlabel("time [h]")
    ax.legend(loc="lower right", bbox_to_anchor=(1, 1), ncol=3)
    ax.set_xlim(0, 24)
    fig.tight_layout()
    fig.savefig(plot_path / f"time_spent_{num_profiles}_profiles.png")
