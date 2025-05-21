from pathlib import Path
from activityassure.profile_category import ProfileCategory
from activityassure.validation_statistics import ValidationStatistics
from activityassure.visualizations.utils import CM_TO_INCH
from matplotlib import pyplot as plt
import pandas as pd


def category_to_plot_label(category: ProfileCategory) -> str:
    """Helper function to convert a profile category to a plot label"""
    category_parts = str(category).split("_", 1)
    if len(category_parts) == 1:
        return category_parts[0]
    return category_parts[1] + '_' + category_parts[0]


def plot_total_time_spent(
        statistics_country_1: dict[ProfileCategory, ValidationStatistics],
        statistics_country_2: dict[ProfileCategory, ValidationStatistics],
        national_statistics: dict[ProfileCategory, ValidationStatistics],
        plot_path: Path,
    ):
    time_activity_distribution = {}
    for _, v in (statistics_country_1 | statistics_country_2 | national_statistics).items():
        time_activity_distribution[v.profile_type] = v.probability_profiles.mean(axis=1) * 24

    # get the column name of the first country
    nat1 = next(iter(national_statistics.keys()))

    fig, ax = plt.subplots(figsize=(16*CM_TO_INCH, 16*CM_TO_INCH))
    combined_df = pd.DataFrame(time_activity_distribution)

    # sort by activity share in first country
    sorted_df = combined_df.sort_values(nat1, ascending=False)  # type: ignore
    
    # combine all activities with a low overall share
    min_share = 0.05 * 24
    summed = sorted_df[sorted_df[nat1] < min_share].sum()
    summed.name = "minor activities"
    
    sorted_df = pd.concat([sorted_df[sorted_df[nat1] >= min_share], summed.to_frame().T])
    sorted_cols = sorted(sorted_df.columns, key=category_to_plot_label)  # type: ignore
    sorted_df[sorted_cols].T.plot(kind='barh', stacked=True, ax=ax)

    ax.legend(loc='lower right', bbox_to_anchor=(1, 1), ncol=3)    
    ax.set_xlim(0, 24)
    fig.tight_layout()
    fig.savefig(plot_path / "time_spent.png")
