import os
from pathlib import Path

from activityassure.visualizations.utils import CM_TO_INCH, ERROR_METRIC_DICT, LABEL_DICT, replace_substrings
from matplotlib import pyplot as plt
from matplotlib.ticker import MultipleLocator
import numpy as np
import pandas as pd
import seaborn as sns

def plot_error_metric_distribution(metrics: pd.DataFrame, output_path: Path):
    output_path /= "histogram.png"
    os.makedirs(output_path.parent, exist_ok=True)
    df = metrics.copy()
    df.index = df.index.map(lambda x: f"{x[0]} - {x[1]}")

    fig, axs = plt.subplots(nrows=5, ncols=1, figsize=(16*CM_TO_INCH, 20*CM_TO_INCH))
    for i, c in enumerate(df.columns, 0):
        if c != "pearson_corr":
            df[c] = df[c].abs()
        sns.histplot(df, x=c, ax=axs[i])
     
        axs[i].set_xlabel(replace_substrings(c, ERROR_METRIC_DICT))
        axs[i].set_ylabel("count")

        # Compute cumulative distribution
        ax2 = axs[i].twinx()
        sorted_data = np.sort(df[c])
        if c == "pearson_corr":
            # For correlation, values close to 1 are best
            axs[i].invert_xaxis()
            sorted_data = sorted_data[::-1]
        cum_dist = np.arange(1, len(sorted_data)+1) / len(sorted_data)
        ax2.plot(sorted_data, cum_dist, color="darkred", label="Cumulative")
        ax2.set_yticks([0, 0.5, 0.75, 0.9, 1])
        ax2.grid(True)
        ax2.set_ylim(0,1)
        pd.DataFrame({"cumulative": cum_dist, c: sorted_data}).to_csv(output_path.parent / f"{c}_cumulative.csv")
            
    fig.tight_layout()
    fig.savefig(output_path, dpi=600)
    fig.savefig(output_path.with_suffix(".svg"))


def plot_elbow_plot_metrics_profile_type_activity(metrics: pd.DataFrame, output_path: Path, zoomed: bool = False):
    """
    Plots an elbow plot of all different profile types and activities and metrics.
    Expects metrics from a per-category validation.
    

    :param metrics: metric dataframe
    :param output_path: output path
    """

    output_path /= "elbow_plot_per_metric_zoomed.png" if zoomed else "elbow_plot_per_metric.png"
    os.makedirs(output_path.parent, exist_ok=True)

    display_count = 50 if zoomed else len(metrics.index)
    df = metrics.copy()
    df.index = df.index.map(lambda x: f"{x[0]} - {x[1]}")

    fig, axs = plt.subplots(nrows=5, ncols=1, figsize=(16*CM_TO_INCH, 16*CM_TO_INCH))
    for i, c in enumerate(df.columns, 0):
        if c != "pearson_corr":
            df[c] = df[c].abs()
        df = df.sort_values(by=c, ascending=True if c == "pearson_corr" else False)
        df["rank"] = range(1, len(df[c])+1)

        sns.lineplot(df[[c, "rank"]].head(display_count), x='rank', y=c, ax=axs[i])
        axs[i].set_ylabel(replace_substrings(c, ERROR_METRIC_DICT))
        axs[i].set_xlabel("")
        if zoomed:
            tick_locs = list(range(0, display_count + 5, 5))
            axs[i].set_xticks(tick_locs)
            axs[i].set_xticklabels(str(loc) for loc in tick_locs)
            axs[i].grid(True, which='major')
            axs[i].xaxis.set_minor_locator(MultipleLocator(1))
            axs[i].grid(True, which='minor')
        axs[i].set_xlim(1, display_count)
            
    fig.tight_layout()
    fig.savefig(output_path, dpi=600)
    fig.savefig(output_path.with_suffix(".svg"))


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
    fig, axs = plt.subplots(nrows=1, ncols=2, figsize=(16*CM_TO_INCH, 6*CM_TO_INCH+top_x*1.5*CM_TO_INCH))

    df2 = metrics[["pearson_corr"]]
    df1 = metrics.drop(columns=["pearson_corr"])
    df1 = df1.abs()


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
        axs[i].set_yticklabels([replace_substrings(label.get_text(), LABEL_DICT).replace("_", " ").replace(" - ", "\n") for label in axs[i].get_yticklabels()])
        fig.tight_layout()
        fig.savefig(output_path, dpi=600)
        fig.savefig(output_path.with_suffix(".svg"))


def plot_bar_plot_metrics_aggregated(metrics: pd.DataFrame, output_path: Path, aggregation_category: str):
    assert aggregation_category in ["activity", "person_profile"]
    output_path_combined = output_path / f"mean_per_{aggregation_category}_combined"
    output_path_error_metrics = output_path / f"mean_per_{aggregation_category}_error_metrics"
    output_path_pearson = output_path / f"mean_per_{aggregation_category}_pearson_corr"
    os.makedirs(output_path.parent, exist_ok=True)
    fig1, axs = plt.subplots(nrows=1, ncols=2, figsize=(10*CM_TO_INCH, 14*CM_TO_INCH))
    if aggregation_category == "person_profile":
        level = 1
        metrics = metrics[metrics.index.get_level_values(level) == 'mean']
        metrics.index = metrics.index.droplevel(level=level).astype(str)
    elif aggregation_category == "activity":
        metrics = metrics.drop("mean")

    df2 = metrics[["pearson_corr"]]
    df1 = metrics.drop(columns=["pearson_corr"])
    df1 = df1.abs()

    for i, df in enumerate([df1, df2]):
        subdf = df.melt(ignore_index=False, var_name='metric')
        sns.barplot(subdf.sort_values(by="value", ascending=True if i == 1 else False).reset_index(), y='index', x='value', orient='h', hue='metric', ax=axs[i])
        axs[i].set_ylabel("")
        axs[i].set_xlabel("")
        axs[i].legend(loc='lower right', bbox_to_anchor=(1, 1.05), ncol=1)
        axs[i].set_yticklabels([replace_substrings(label.get_text(), LABEL_DICT).replace("_", " ").replace(" - ", "\n") for label in axs[i].get_yticklabels()])
        fig1.tight_layout()
        fig1.savefig((output_path_combined).with_suffix(".png"), dpi=600)
        fig1.savefig((output_path_combined).with_suffix(".svg"))

        # Single plots
        fig2, ax = plt.subplots(nrows=1, ncols=1, figsize=(5*CM_TO_INCH, 14*CM_TO_INCH))
        sns.barplot(subdf.sort_values(by="value", ascending=True if i == 1 else False).reset_index(), y='index', x='value', hue='metric', orient='h', ax=ax)
        ax.set_yticklabels([replace_substrings(label.get_text(), LABEL_DICT).replace("_", " ") for label in ax.get_yticklabels()])
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.legend(loc='lower right', bbox_to_anchor=(1, 1.05), ncol=1)
        single_plot_output_path = output_path_error_metrics if i == 0 else output_path_pearson
        fig2.tight_layout()
        fig2.savefig(single_plot_output_path.with_suffix(".png"), dpi=600)
        fig2.savefig(single_plot_output_path.with_suffix(".svg"))

