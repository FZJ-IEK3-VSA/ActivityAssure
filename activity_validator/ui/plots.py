from datetime import datetime, timedelta
from pathlib import Path
from dash import html, dcc  # type: ignore
import dash_bootstrap_components as dbc  # type: ignore
import plotly.express as px  # type: ignore
from plotly.graph_objects import Figure  # type: ignore

import pandas as pd
from activity_validator.hetus_data_processing import activity_profile
from activity_validator.lpgvalidation import comparison_metrics
from activity_validator.ui import data_utils
from activity_validator.ui import datapaths


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
    return titled_card(dcc.Graph(figure=figure), title)


def get_date_range(num_values: int):
    # generate 24h time range starting at 04:00
    resolution = timedelta(days=1) / num_values
    start_time = datetime.strptime("04:00", "%H:%M")
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


def stacked_prob_curves(filepath: Path | None, area: bool = True) -> Figure | None:
    if filepath is None or not filepath.is_file():
        return None
    # load the correct file
    _, data = activity_profile.load_df(filepath)
    # transpose data for plotting
    data = data.T
    time_values = get_date_range(len(data))
    # select plot type
    plotting_func = px.area if area else px.line
    # plot the data
    fig = plotting_func(
        data,
        x=time_values,
        y=data.columns,
    )
    return fig


def update_prob_curves(profile_type_str: str, directory: Path, area: bool = True):
    # load the correct file and plot it
    profile_type = data_utils.ptype_from_label(profile_type_str)
    filepath = data_utils.get_file_path(directory, profile_type)
    figure = stacked_prob_curves(filepath, area)
    if not figure:
        return replacement_text()
    return [dcc.Graph(figure=figure)]


def prob_curve_per_activity(
    profile_type: activity_profile.ProfileType, subdir: str
) -> dict[str, dcc.Graph]:
    # get the path of the validation and the input file
    path_val = data_utils.get_file_path(
        datapaths.validation_path / subdir, profile_type
    )
    path_in = data_utils.get_file_path(datapaths.input_data_path / subdir, profile_type)
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
    validation_data = validation_data.T
    input_data = input_data.T * -1
    data_per_activity = join_to_pairs(validation_data, input_data)

    # create the plots
    figures = {}
    for activity, data in data_per_activity.items():
        figure = px.line(data)
        # fill the areas between the curves and the x-axis
        figure.update_traces(fill="tonexty", selector={"name": "Validation"})
        figure.update_traces(fill="tozeroy", selector={"name": "Input"})
        # make the y-axis range symmetric
        max_y = data.abs().max(axis=None)
        figure.update_yaxes(range=[-max_y, max_y])
        figures[activity] = dcc.Graph(figure=figure)
    return figures


def histogram_per_activity(
    profile_type: activity_profile.ProfileType,
    subdir: Path,
    duration_data: bool = False,
) -> dict[str, dcc.Graph]:
    """
    Generates a set of histogram plots, one for each activity type.
    Each histogram compares the validation data to the matching input
    data.

    :param profile_type: the selected profile type
    :param subdir: the data subdirectory to use, which must contain
                   data per activity type in each file
    :param duration_data: whether to convert the data to timedeltas, defaults to False
    :return: a list of Cards containing the individual plots
    """
    # determine file paths for validation and input data
    path_val = data_utils.get_file_path(
        datapaths.validation_path / subdir, profile_type
    )
    path_in = data_utils.get_file_path(datapaths.input_data_path / subdir, profile_type)
    if path_val is None or path_in is None:
        return {}

    # load both files
    _, validation_data = activity_profile.load_df(path_val, duration_data)
    _, input_data = activity_profile.load_df(path_in, duration_data)

    data_per_activity = join_to_pairs(validation_data, input_data)

    # create the plots for all activity types and wrap them in Cards
    # TODO alternative: use ecdf instead of histogram for a sum curve
    figures = {
        activity: dcc.Graph(figure=px.histogram(d, barmode="overlay"))
        for activity, d in data_per_activity.items()
    }
    return figures


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


def round_num(value, digits: int = -1) -> float | str:
    """
    Calls the round function on numbers, and returns
    everything else unchanged.

    :param value: the value to round
    :param digits: the digits to round to
    :return: the rounded value
    """
    if value is None or pd.isna(value):
        return "n/a"
    return round(value, digits) if digits >= 0 else value


def kpi_table(
    profile_type: activity_profile.ProfileType, subdir: Path
) -> dict[str, dcc.Graph]:
    """
    Generates a KPI table for each activity

    :param profile_type: the profile type
    :param subdir: _description_
    :return: _description_
    """
    # determine file path for the metrics
    path = data_utils.get_file_path(datapaths.input_data_path / subdir, profile_type)
    if path is None:
        return {}
    _, metrics = comparison_metrics.ValidationMetrics.load(path)
    digits = 6
    tables = {
        a: dbc.Table(
            [
                html.Tr([html.Td("Probability Curve Difference")]),
                html.Tr([html.Td("MEA"), html.Td(round(metrics.mea[a], digits))]),
                html.Tr([html.Td("MSE"), html.Td(round(metrics.rmse[a] ** 2, digits))]),
                html.Tr(),
                html.Tr([html.Td("Difference of Activity Frequencies")]),
                html.Tr(
                    [
                        html.Td("Kolmogorov-Smirnov p-Value"),
                        html.Td(round_num(metrics.ks_frequency_p[a])),
                    ]
                ),
                html.Tr(),
                html.Tr([html.Td("Difference of Activity Durations")]),
                html.Tr(
                    [
                        html.Td("Kolmogorov-Smirnov p-Value"),
                        html.Td(round_num(metrics.ks_duration_p[a])),
                    ]
                ),
            ]
        )
        for a in metrics.mea.index
    }
    return tables
