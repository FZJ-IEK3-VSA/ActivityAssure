"""
Generates metric heatmaps. Each metric heatmap gives an overview on a 
single metric (e.g., RMSE) for all combinations of profile types.
"""


from pathlib import Path
import pandas as pd
import plotly.express as px

from activity_validator.hetus_data_processing.activity_profile import ProfileType
from activity_validator.lpgvalidation import comparison_metrics


def convert_to_metric_dataframe(
    metrics_dict: dict[str, dict[str, comparison_metrics.ValidationMetrics]]
) -> dict[str, pd.DataFrame]:
    """
    Converts a nested metric dict to a set of dataframes, one for each metric

    :param metrics_dict: a nested dict that contains metrics for each combination of
                         input and validation profile types
    :return: a dict mapping the metric names to the respective dataframes
             containing the metric values
    """
    total_metrics_dicts: dict[str, dict[str, dict[str, float]]] = {}
    for p1, metrics_for_one_category in metrics_dict.items():
        for p2, metrics in metrics_for_one_category.items():
            total_metrics = metrics.get_metric_sums()
            for name, value in total_metrics.items():
                total_metrics_dicts.setdefault(name, {}).setdefault(str(p1), {})[
                    str(p2)
                ] = value
    dataframes = {k: pd.DataFrame(v) for k, v in total_metrics_dicts.items()}
    return dataframes


def plot_metrics_heatmap(data: pd.DataFrame):
    """
    Plots a single metric heatmap

    :param data: the dataframe containing the metric values;
                 index and column names are the profile types
    """
    fig = px.imshow(data, title=data.Name)
    fig.show()
    # decrease font size for image file to include all axis labels
    fig.update_layout(font_size=9, title_font_size=18)
    path = Path("data/lpg/results/plots")
    path.mkdir(parents=True, exist_ok=True)
    file = path / f"{data.Name}_heatmap.svg"
    fig.write_image(file)


def plot_metrics_heatmaps(metrics_dict):
    """
    Uses a full set of metrics between each combination
    of input and validation profile types to generate a
    set of heatmaps, one for each validation metric.

    :param metrics_dict: a full, symmetric set of metrics,
                         one for each combination of input
                         and validation profile types
    """
    dataframes = convert_to_metric_dataframe(metrics_dict)
    for name, df in dataframes.items():
        # df = df.reindex(df.columns)
        df = df[df.index]
        df.Name = name
        plot_metrics_heatmap(df)
