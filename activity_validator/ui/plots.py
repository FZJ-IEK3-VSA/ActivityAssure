import dataclasses
from datetime import datetime, timedelta
import math
from pathlib import Path
from dash import html, dcc  # type: ignore
import dash_bootstrap_components as dbc  # type: ignore
import numpy as np
import plotly.express as px  # type: ignore
from plotly.graph_objects import Figure  # type: ignore

import pandas as pd
from activity_validator.hetus_data_processing import activity_profile, hetus_constants
from activity_validator.lpgvalidation import comparison_metrics, validation_data
from activity_validator.ui import data_utils
from activity_validator.ui import datapaths

# general config for all graphs
GLOBAL_GRAPH_CONFIG = {
    "toImageButtonOptions": {
        "format": "svg",  # one of png, svg, jpeg, webp
        # "filename": "custom_image",
    }
}


def replacement_text(text: str = "No data available"):
    """
    Function to generate a default replacement text for when
    the data to display is missing.

    :param text: the text to display, defaults to "No data available"
    :return: the display element
    """
    return html.Div(children=[text], style={"textAlign": "center"})


def titled_card(content, title: str = "") -> dbc.Card:
    """
    Embeds any content in a card with an optional title

    :param content: content for the card
    :param title: title for the card
    :return: the resulting Card object
    """
    if not isinstance(content, list):
        content = [content]
    t = [html.H3(title, style={"textAlign": "center"})] if title else []
    return dbc.Card(dbc.CardBody(children=t + content))


def single_plot_card(figure: Figure, title: str = "") -> dbc.Card:
    """
    Embeds a single plot in a card with a title

    :param figure: figure object of the plot
    :param title: title of the plot
    :return: the Card object containing the plot
    """
    return titled_card(dcc.Graph(figure=figure, config=GLOBAL_GRAPH_CONFIG), title)


def get_date_range(num_values: int):
    # generate 24h time range starting at 04:00
    resolution = timedelta(days=1) / num_values
    start_time = datetime.strptime("04:00", "%H:%M")
    start_time = datetime(1900, 1, 1) + hetus_constants.PROFILE_OFFSET
    end_time = start_time + timedelta(days=1) - resolution
    time_values = pd.date_range(start_time, end_time, freq=resolution)
    return time_values


def join_to_pairs(
    validation_data: pd.DataFrame, input_data: pd.DataFrame
) -> dict[str, pd.DataFrame]:
    """
    Splits two DataFrames with the same set of columns and
    joins columns of the same name from the different DataFrames.

    :param validation_data: first data set
    :param input_data: second data set
    :return: dict of new DataFrames, each containing one column from
             each of the two original DataFrames, grouped by column
             name
    """
    # join the valiation data with the input data for each activity type
    data_sets: dict[str, pd.DataFrame] = {}
    for col in validation_data.columns:
        d_val = validation_data[col]
        if col in input_data:
            d_in = input_data[col]
        else:
            # no input data for this activity type: create an empty column
            d_in = pd.Series([], dtype=d_val.dtype)
        # set new names for the curves
        d_val.name = "Validation"
        d_in.name = "Input"
        joined = pd.concat([d_val, d_in], axis=1)
        data_sets[col] = joined
    return data_sets


def stacked_prob_curves(filepath: Path | None) -> Figure | None:
    if filepath is None or not filepath.is_file():
        return None
    # load the correct file
    _, data = activity_profile.load_df(filepath)
    # transpose data for plotting
    data = data.T
    time_values = get_date_range(len(data))
    # plot the data
    fig = px.area(
        data,
        x=time_values,
        y=data.columns,
    )
    fig.update_xaxes(tickformat="%H:%M")
    return fig


def update_stacked_prob_curves(profile_type_str: str, directory: Path):
    # load the correct file and plot it
    profile_type = data_utils.ptype_from_label(profile_type_str)
    filepath = data_utils.get_file_path(directory, profile_type)
    figure = stacked_prob_curves(filepath)
    if not figure:
        return replacement_text()

    data_utils.save_plot(
        figure,
        "probability profiles",
        name="validation" if "valid" in str(directory).lower() else "input",
        profile_type=profile_type,
    )
    return [dcc.Graph(figure=figure, config=GLOBAL_GRAPH_CONFIG)]


def stacked_diff_curve(path_valid: Path | None, path_in: Path | None):
    if (
        path_valid is None
        or not path_valid.is_file()
        or path_in is None
        or not path_in.is_file()
    ):
        return None
    # load the correct files
    _, data_val = activity_profile.load_df(path_valid)
    _, data_in = activity_profile.load_df(path_in)

    # get the probability profile differences
    diff = comparison_metrics.calc_probability_curves_diff(data_val, data_in)
    diff = diff.T
    time_values = get_date_range(len(diff))
    # plot the data
    fig = px.line(
        diff,
        x=time_values,
        y=diff.columns,
    )
    fig.update_xaxes(tickformat="%H:%M")
    return fig


def prob_curve_per_activity(
    profile_type_val: activity_profile.ProfileType,
    profile_type_in: activity_profile.ProfileType,
    subdir: Path | str,
) -> dict[str, dcc.Graph]:
    # get the path of the validation and the input file
    path_val = data_utils.get_file_path(
        datapaths.validation_path / subdir, profile_type_val
    )
    path_in = data_utils.get_file_path(
        datapaths.input_data_path / subdir, profile_type_in
    )
    if path_val is None or path_in is None:
        return {}
    # load both files
    _, validation_data = activity_profile.load_df(path_val)
    _, input_data = activity_profile.load_df(path_in)

    # assign time values for the timesteps
    time_values = get_date_range(len(validation_data.columns))
    validation_data.columns = time_values
    input_data.columns = time_values
    # determine common index with all activity types
    common_index = validation_data.index.union(input_data.index)
    # add rows full of zeros for missing activity types
    validation_data = validation_data.reindex(common_index, fill_value=0)
    input_data = input_data.reindex(common_index, fill_value=0)
    validation_data = validation_data.T * -1
    input_data = input_data.T
    data_per_activity = join_to_pairs(validation_data, input_data)

    # create the plots
    figures = {}
    for activity, data in data_per_activity.items():
        figure = px.line(data)
        # fill the areas between the curves and the x-axis
        figure.update_traces(fill="tozeroy", selector={"name": "Input"})
        figure.update_traces(fill="tozeroy", selector={"name": "Validation"})
        # use the same y-axis range for all plots
        figure.update_yaxes(range=[-1, 1])
        figure.update_xaxes(tickformat="%H:%M")
        figures[activity] = dcc.Graph(figure=figure, config=GLOBAL_GRAPH_CONFIG)
    return figures


def histogram_per_activity(
    ptype_val: activity_profile.ProfileType,
    ptype_in: activity_profile.ProfileType,
    subdir: Path | str,
    duration_data: bool = False,
) -> dict[str, dcc.Graph]:
    """
    Generates a set of histogram plots, one for each activity type.
    Each histogram compares the validation data to the matching input
    data.

    :param ptype_val: the selected profile type of the validation data
    :param ptype_in: the selected profile type of the input data
    :param subdir: the data subdirectory to use, which must contain
                   data per activity type in each file
    :param duration_data: whether to convert the data to timedeltas, defaults to False
    :return: a list of Cards containing the individual plots
    """
    # determine file paths for validation and input data
    path_val = data_utils.get_file_path(datapaths.validation_path / subdir, ptype_val)
    path_in = data_utils.get_file_path(datapaths.input_data_path / subdir, ptype_in)
    if path_val is None or path_in is None:
        return {}

    # load both files
    _, validation_data = activity_profile.load_df(path_val, duration_data)
    _, input_data = activity_profile.load_df(path_in, duration_data)
    if duration_data:
        # TODO workaround: https://github.com/plotly/plotly.py/issues/799
        validation_data += datetime(2023, 1, 1)
        input_data += datetime(2023, 1, 1)
        title = "Activity Durations"
        xaxis_title = "Activity duration"
    else:
        title = "Activity Frequencies"
        xaxis_title = "Activity repetitions per day"

    data_per_activity = join_to_pairs(validation_data, input_data)

    # create the plots for all activity types and wrap them in Cards
    # TODO alternative: use ecdf instead of histogram for a sum curve
    figures = {
        activity: px.histogram(d, barmode="overlay", histnorm="percent")
        for activity, d in data_per_activity.items()
    }
    for a, f in figures.items():
        f.update_layout(title=f'"{a}" {title}', xaxis_title=xaxis_title)
    graphs = {
        a: dcc.Graph(figure=f, config=GLOBAL_GRAPH_CONFIG) for a, f in figures.items()
    }
    return graphs


def stacked_bar_activity_share(paths: dict[str, Path]) -> Figure:
    """
    Generates a stacked bar chart to show differences in overall activity
    shares per profile type.

    :param paths: file paths for each profile type
    :return: bar chart figure
    """
    # load all activity probability files
    datasets = {k: activity_profile.load_df(path)[1] for k, path in paths.items()}
    # calculate the average probabilities per profile type
    data = pd.DataFrame({title: data.mean(axis=1) for title, data in datasets.items()})
    # add the overall probabilities
    data["Overall"] = data.mean(axis=1)
    return px.bar(data.T)  # , x=data.columns, y=data.index)


def round_kpi(value, digits: int = -1) -> float | str:
    """
    Replaces None or NAN with 'n/a', and optionally
    rounds numbers

    :param value: the value to round
    :param digits: the digits to round to
    :return: the rounded value
    """
    if value is None or pd.isna(value):
        return "n/a"
    return round(value, digits) if digits >= 0 else value


def format_timedelta(td):
    # Extract days, hours, minutes, and seconds
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Create a formatted string
    formatted_str = f"{hours:02}:{minutes:02}:{seconds:02}"

    if days > 0:
        formatted_str = f"{days} days, {formatted_str}"
    return formatted_str


def timedelta_to_str(t: timedelta) -> str:
    # python's default representation of negative timedeltas is unintuitive
    if t < timedelta(0):
        sign = "-"
        t *= -1
    else:
        sign = ""
    return sign + format_timedelta(t)


def bias_to_str(value: float) -> str:
    """
    Converts the bias from a float in range [-1, 1] to
    a str representation of a timedelta in range [-1 day, 1 day].
    This emphasizes its meaning: the average difference of time
    spent per day on an activity category.

    :param value: bias value
    :return: str timedelta representation
    """
    if not math.isfinite(value):
        return "Nan/Inf"
    td = timedelta(value)
    return timedelta_to_str(td)


def kpi_table_rows(
    metrics: comparison_metrics.ValidationMetrics,
    activity: str,
    title: str = "",
    extended: bool = True,
):
    digits = 6
    bold = {"fontWeight": "bold"}
    title_rows = [html.Tr([html.Td(title)], style=bold)] if title else []
    basic_rows = [
        html.Tr([html.Td("MAE"), html.Td(round_kpi(metrics.mae[activity], digits))]),
        html.Tr(
            [
                html.Td("Bias [time]"),
                html.Td(bias_to_str((metrics.bias[activity]))),
            ]
        ),
        html.Tr(
            [html.Td("RMSE"), html.Td(round_kpi(metrics.rmse[activity] ** 2, digits))]
        ),
        html.Tr(
            [
                html.Td("Wasserstein distance"),
                html.Td(round_kpi(metrics.wasserstein[activity], digits)),
            ]
        ),
    ]
    if extended:
        extended_rows = [
            html.Tr(
                [
                    html.Td("Pearson correlation"),
                    html.Td(round_kpi(metrics.pearson_corr[activity], digits)),
                ]
            )
        ]
    else:
        extended_rows = []
    return title_rows + basic_rows + extended_rows


def kpi_table(
    ptype_val: activity_profile.ProfileType, ptype_in: activity_profile.ProfileType
) -> dict[str, dcc.Graph]:
    """
    Generates a KPI table for each activity.

    :param ptype_val: the selected profile type of the validation data
    :param ptype_in: the selected profile type of the input data
    :return: dict of all KPI tables
    """
    try:
        # load the statistics for validation and input data
        data_val = validation_data.ValidationData.load(
            datapaths.validation_path, ptype_val
        )
        data_in = validation_data.ValidationData.load(
            datapaths.input_data_path, ptype_in
        )
    except RuntimeError:
        return {}

    shares = data_val.probability_profiles.mean(axis=1)

    # get normal, scaled and normalized metrics
    _, metrics = comparison_metrics.calc_comparison_metrics(
        data_val, data_in, add_kpi_means=False
    )

    scaled = metrics.get_scaled(shares)

    _, metrics_normed = comparison_metrics.calc_comparison_metrics(
        data_val, data_in, True, add_kpi_means=False
    )
    tables = {
        a: dbc.Table(
            kpi_table_rows(metrics, a, "Probability Curves Absolute")
            + kpi_table_rows(
                scaled,
                a,
                "Probability Curves Relative to duration in validation data",
                False,
            )
            + kpi_table_rows(metrics_normed, a, "Probability Curves Normalized", False)
        )
        for a in metrics.mae.index
    }
    return tables
