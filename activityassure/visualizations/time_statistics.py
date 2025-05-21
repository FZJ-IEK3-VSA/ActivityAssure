from activityassure.profile_category import ProfileCategory
from activityassure.validation_statistics import ValidationStatistics
from activityassure.visualizations.utils import CM_TO_INCH
from matplotlib import pyplot as plt
import pandas as pd


def plot_total_time_spent(statistics_country_1: dict[ProfileCategory, ValidationStatistics], statistics_country_2: dict[ProfileCategory, ValidationStatistics]):
    time_activity_distribution = {}
    for _, v in (statistics_country_1 | statistics_country_2).items():
        time_activity_distribution[v.profile_type] = v.probability_profiles.mean(axis=1) * 24

    fig, ax = plt.subplots(figsize=(16*CM_TO_INCH, 16*CM_TO_INCH))
    combined_df = pd.DataFrame(time_activity_distribution)
    sorted_cols = sorted(combined_df.columns, key=lambda x: str(x).split('_', 1)[1] + '_' + str(x).split('_', 1)[0])
    combined_df[sorted_cols].T.plot(kind='barh', stacked=True, ax=ax)

    ax.legend(loc='lower right', bbox_to_anchor=(1, 1), ncol=3)    
    ax.set_xlim(0, 24)
    fig.tight_layout()
    fig.savefig("test.png") # TODO: save in proper location

    # TODO: plot total time spent using national dataset (in separate plot?)
    # TODO: combine small shares
    # TODO: sort by share so that largest shares are on the left
