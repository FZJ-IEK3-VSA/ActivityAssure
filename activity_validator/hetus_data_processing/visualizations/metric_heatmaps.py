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
    metrics_dict: dict[
        ProfileType, dict[ProfileType, comparison_metrics.ValidationMetrics]
    ]
) -> dict[str, pd.DataFrame]:
    """
    Converts a nested metric dict to a set of dataframes, one for each metric

    :param metrics_dict: a nested dict that contains metrics for each combination of
                         input and validation profile types
    :return: a dict mapping the metric names to the respective dataframes
             containing the metric values
    """
    total_metrics_dicts: dict[str, dict[ProfileType, dict[ProfileType, float]]] = {}
    for p1, metrics_for_one_category in metrics_dict.items():
        for p2, metrics in metrics_for_one_category.items():
            total_metrics = metrics.get_metric_sums()
            for name, value in total_metrics.items():
                total_metrics_dicts.setdefault(name, {}).setdefault(p1, {})[p2] = value
    dataframes = {k: pd.DataFrame(v) for k, v in total_metrics_dicts.items()}
    return dataframes


def plot_metrics_heatmap(data: pd.DataFrame, output_path: Path):
    """
    Plots a single metric heatmap

    :param data: the dataframe containing the metric values;
                 index and column names are the profile types
    :param output_path: base output directory
    """
    # turn index to str
    data.index = pd.Index([str(x) for x in data.index])
    data.columns = pd.Index([str(x) for x in data.columns])
    fig = px.imshow(data, title=data.Name)
    # fig.show()
    # decrease font size for image file to include all axis labels
    fig.update_layout(font_size=9, title_font_size=18)
    path = output_path / "plots"
    path.mkdir(parents=True, exist_ok=True)
    file = path / f"heatmap_{data.Name}.svg"
    fig.write_image(file)


def make_symmetric(data: pd.DataFrame, sparse: bool = True) -> pd.DataFrame:
    """
    Makes a metrics dataframe symmetric, that means colum and row indices are
    aligned. This improves heatmap readibility.

    :param data: metrics dataframe
    :param sparse: whether NaN columns shall be added in case of missing profile types
                   in the input data, defaults to True
    :return: the reordered metrics dataframe
    """
    if set(data.columns) == set(data.index):
        # only need to reorder the columns
        return data[data.index]

    # Remark: each column must be contained in the index (not necessarily
    # the other way round).

    if sparse:
        # make the dataframe square, with colum and row index being exactly the same
        d = pd.DataFrame(columns=data.index)
        for col in d.columns:
            if col in data.columns:
                d[col] = data[col]
            else:
                d[col] = pd.NA
        return d

    # put the profile types that occur in both indices first, and the rest after
    index = list(data.columns) + [x for x in data.index if x not in data.columns]
    return data.reindex(index)


def order_index(data: pd.DataFrame) -> pd.DataFrame:
    """
    Reorders the dataframe rows based on the different profile types
    in the index to improve heatmap readability. That means, similar
    categories (e.g., only different sex) are next to each other, while
    more different categories (e.g. 'work'-'no work) are far apart.

    :param data: metrics dataframe
    :return: ordered metrics dataframe
    """
    new_index = sorted(
        data.index, key=lambda p: (p.country, p.day_type, p.work_status, p.sex)
    )
    return data.reindex(new_index)


def plot_metrics_heatmaps(metrics_dict, output_path: Path):
    """
    Uses a full set of metrics between each combination
    of input and validation profile types to generate a
    set of heatmaps, one for each validation metric.

    :param metrics_dict: a full, symmetric set of metrics,
                         one for each combination of input
                         and validation profile types
    :param output_path: base output directory
    """
    dataframes = convert_to_metric_dataframe(metrics_dict)
    for name, df in dataframes.items():
        df = order_index(df)
        df = make_symmetric(df)
        df.Name = name
        plot_metrics_heatmap(df, output_path)
