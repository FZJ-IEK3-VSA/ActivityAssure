import os
from pathlib import Path

from matplotlib import pyplot as plt
import pandas as pd
import seaborn as sns

def plot_bar_plot_metrics_profile_type_activity(metrics: pd.DataFrame, output_path: Path, top_x: int = 3):
    """
    Plots a barplot of all different profile types and activities and metrics.
    Expects metrics from a per-category validation.
    The "top" values are the ones indicating the highest deviance between the values, i.e., for most error
    metrics, this is the highest numeric value, whereas for correlation it's the lowest values.

    :param metrics: metric dataframe
    :param output_path: output path
    """

    output_path /= f"top_{top_x}_per_metric.png"
    os.makedirs(output_path.parent, exist_ok=True)
    fig, axs = plt.subplots(nrows=1, ncols=2, figsize=(9, 4))
    # Plot
    df2 = metrics[["pearson_corr"]]
    df1 = metrics.drop(columns=["pearson_corr"])
    df1 = df1.abs()
    print(df1.columns)

    for i, df in enumerate([df1, df2]):
        df.index = df.index.map(lambda x: f"{x[0]} - {x[1]}")
        top5 = []

        for c in df.columns:
            if i == 1:
                top5 = top5 + df[c].nsmallest(top_x).index.tolist()
            else:
                top5 = top5 + df[c].nlargest(top_x).index.tolist()


        top5 = list(set(top5))
        top5 = df.loc[top5,:].sum(axis=1).sort_values(ascending=False).index.tolist()

        subdf = df.melt(ignore_index=False, var_name='metric')
        sns.barplot(subdf.loc[top5,:].reset_index(), y='index', x='value', orient='h', hue='metric', ax=axs[i])
        axs[i].set_ylabel("")
        axs[i].legend(loc='lower right', bbox_to_anchor=(1, 1.05), ncol=2)
        axs[i].set_yticklabels([l.get_text().replace(" - ", "\n") for l in axs[i].get_yticklabels()])
        fig.tight_layout()
        fig.savefig(output_path)