"""
Generates metric heatmaps. Each metric heatmap gives an overview on a 
single metric (e.g., RMSE) for all combinations of profile types.
"""

import logging
from pathlib import Path
import warnings
import pandas as pd
import plotly.express as px  # type: ignore

from activity_validator.hetus_data_processing.activity_profile import ProfileType
from activity_validator.lpgvalidation import comparison_metrics


def clean_activity_name(activity_name: str) -> str:
    """
    Sanitizes an activity name by removing special characters
    so it can be used as a file name.

    :param activity_name: activity name
    :return: sanitized activity name
    """
    return activity_name.replace("/", "-")


def make_metrics_comparable(data: pd.DataFrame) -> pd.DataFrame:
    """
    Can be used for dataframes which contain different types of metrics
    (e.g. MAE and Pearson correlation coefficient) to facilitate
    comparing them by transforming their value ranges.

    :param data: metrics data
    :return: adapted data
    """
    data = normalize_min_max(data)
    data = reverse_pearson(data)
    data = select_metrics(data)
    return data


def normalize_min_max(data: pd.DataFrame) -> pd.DataFrame:
    """
    Apply min-max-normalization to change the value range of all
    metrics to [0, 1].
    """
    # ignore performance warning (dataframe is small)
    with warnings.catch_warnings():
        warnings.simplefilter(action="ignore", category=pd.errors.PerformanceWarning)
        return (data - data.min()) / (data.max() - data.min())


def reverse_pearson(data: pd.DataFrame) -> pd.DataFrame:
    """
    Reverse value range of pearson correlation coefficient, so that
    low values indicate better fit, as with the other metrics

    :param data: metrics data
    :return: metrics data with adapted pearson column
    """
    pearson_column = "pearson_corr"
    if pearson_column in data.columns:
        # the lowest observed value of the pearson correlation coefficient was only slightly
        # below zero (no correlation). Strongly negative values indicating a negative
        # correlation are not to be expected.
        data[pearson_column] = data[pearson_column].max() - data[pearson_column].abs()
    return data


def select_metrics(data: pd.DataFrame) -> pd.DataFrame:
    """Select only the relevant metrics to compare in the heatmap"""
    columns = ["mae", "rmse", "wasserstein", "bias", "pearson_corr"]
    return data[columns]


def convert_to_metric_mean_dataframe(
    metrics_dict: dict[
        ProfileType, dict[ProfileType, comparison_metrics.ValidationMetrics]
    ]
) -> dict[str, pd.DataFrame]:
    """
    Converts a nested metric dict to a set of dataframes, one for each metric.
    Calculates the mean metrics for each profile type (across all activities).

    :param metrics_dict: a nested dict that contains metrics for each combination of
                         input and validation profile types
    :return: a dict mapping the metric names to the respective dataframes
             containing the metric values
    """
    total_metrics_dicts: dict[str, dict[ProfileType, dict[ProfileType, float]]] = {}
    for p1, metrics_for_one_category in metrics_dict.items():
        for p2, metrics in metrics_for_one_category.items():
            total_metrics = metrics.get_metric_means()
            for name, value in total_metrics.items():
                total_metrics_dicts.setdefault(name, {}).setdefault(p1, {})[p2] = value
    dataframes = {k: pd.DataFrame(v) for k, v in total_metrics_dicts.items()}
    return dataframes


def convert_to_metric_dataframe_per_activity(
    metrics_dict: dict[
        ProfileType, dict[ProfileType, comparison_metrics.ValidationMetrics]
    ]
) -> dict[str, dict[str, pd.DataFrame]]:
    """
    Converts a nested metric dict to a set of dataframes, one for each metric and
    activity.

    :param metrics_dict: a nested dict that contains metrics for each combination of
                         input and validation profile types
    :return: a nested dict mapping the metric names and activity names to the
             respective dataframes containing the metric values
    """
    total_metrics_dicts: dict[
        str, dict[str, dict[ProfileType, dict[ProfileType, float]]]
    ] = {}
    for p1, metrics_for_one_category in metrics_dict.items():
        for p2, metrics in metrics_for_one_category.items():
            metric_df = metrics.to_dataframe()
            # iterate through all columns (one per metric)
            for kpi_name, kpi_values in metric_df.items():
                for activity, value in kpi_values.items():
                    total_metrics_dicts.setdefault(str(kpi_name), {}).setdefault(
                        str(activity), {}
                    ).setdefault(p1, {})[p2] = value
    dataframes = {
        kpi: {act: pd.DataFrame(v) for act, v in d.items()}
        for kpi, d in total_metrics_dicts.items()
    }
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
    fig = px.imshow(
        data,
        title=data.Name,
        labels={"x": "Input Data Category", "y": "Validation Data Category"},
        # zmin=-1,
        # zmax=1,
    )
    # fig.show()
    # decrease font size for image file to include all axis labels
    fig.update_layout(font_size=8, title_font_size=18)
    output_path.mkdir(parents=True, exist_ok=True)
    file = output_path / f"heatmap_{data.Name}.png"
    try:
        fig.write_image(file, engine="kaleido")
    except Exception as e:
        logging.error(f"Could not create KPI heatmap {data.Name}: {e}")


def make_symmetric(data: pd.DataFrame, sparse: bool = True) -> pd.DataFrame:
    """
    Makes a metrics dataframe symmetric, that means colum and row indices are
    aligned. This improves heatmap readability.

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


def order_profile_type_index(data: pd.DataFrame) -> pd.DataFrame:
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


def plot_category_comparison(metrics_dict, output_path: Path):
    """
    Uses a full set of metrics between each combination
    of input and validation profile types to generate a
    set of heatmaps, one for each validation metric.

    :param metrics_dict: a full, symmetric set of metrics,
                         one for each combination of input
                         and validation profile types
    :param output_path: base output directory
    """
    dataframes = convert_to_metric_mean_dataframe(metrics_dict)
    for name, df in dataframes.items():
        df = order_profile_type_index(df)
        df = make_symmetric(df)
        df.Name = name
        plot_metrics_heatmap(df, output_path)


def plot_category_comparison_per_activity(metrics_dict, output_path: Path):
    """
    Uses a full set of metrics between each combination
    of input and validation profile types to generate a
    set of heatmaps, one per activity per validation metric.

    :param metrics_dict: a full, symmetric set of metrics,
                         one for each combination of input
                         and validation profile types
    :param output_path: base output directory
    """
    dataframes = convert_to_metric_dataframe_per_activity(metrics_dict)
    for name, d in dataframes.items():
        path = output_path / name
        for activity, df in d.items():
            df = order_profile_type_index(df)
            df = make_symmetric(df)
            # replace invalid characters for file names
            clean_act_name = clean_activity_name(activity)
            df.Name = f"{name}_{clean_act_name}"
            plot_metrics_heatmap(df, path)


def plot_metrics_by_profile_type(metrics: pd.DataFrame, output_path: Path):
    """
    Plots a heatmap of all different metrics and profile types.
    Expects metrics from a per-category validation.

    :param metrics: metric dataframe
    :param output_path: output path
    """
    output_path /= "metrics x profile_type"
    level = 1
    grouped = metrics.groupby(level=level, sort=False)
    for activity, df in grouped:
        df = df.droplevel(level)
        df = order_profile_type_index(df)
        df = make_metrics_comparable(df)
        df.Name = clean_activity_name(activity)  # type: ignore
        plot_metrics_heatmap(df, output_path)


def plot_metrics_by_activity(metrics: pd.DataFrame, output_path: Path):
    """
    Plots a heatmap of all different metrics and activities.
    Expects metrics from a per-category validation.

    :param metrics: metric dataframe
    :param output_path: output path
    """
    output_path /= "metrics x activity"
    level = 0
    grouped = metrics.groupby(level=level, sort=False)
    for profile_type, df in grouped:
        df = df.droplevel(level)
        df = make_metrics_comparable(df)
        df.Name = str(profile_type)
        plot_metrics_heatmap(df, output_path)


def plot_profile_type_by_activity(metrics: pd.DataFrame, output_path: Path):
    """
    Plots a heatmap of all different profile types and activities.
    Expects metrics from a per-category validation.

    :param metrics: metric dataframe
    :param output_path: output path
    """
    output_path /= "profile_type x activity"
    mean_idx = comparison_metrics.ValidationMetrics.mean_column
    for metric_name in metrics.columns:
        df = metrics[metric_name].unstack(level=1)
        if mean_idx in df.columns:
            # if mean is contained, move it to the right side
            columns = list(df.columns)
            columns.remove(mean_idx)
            columns += [mean_idx]
            df = df[columns]
        df.Name = metric_name
        plot_metrics_heatmap(df, output_path)
