from datetime import datetime, timedelta
from pathlib import Path
from dash import html, dcc  # type: ignore
import dash_bootstrap_components as dbc  # type: ignore
import plotly.express as px  # type: ignore

import pandas as pd
from activity_validator.hetus_data_processing import activity_profile
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


def get_date_range(num_values: int):
    # generate 24h time range starting at 04:00
    resolution = timedelta(days=1) / num_values
    start_time = datetime.strptime("04:00", "%H:%M")
    end_time = start_time + timedelta(days=1) - resolution
    time_values = pd.date_range(start_time, end_time, freq=resolution)
    return time_values


def convert_to_timedelta(data: pd.DataFrame) -> None:
    for col in data.columns:
        data[col] = pd.to_timedelta(data[col])


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
        if col not in input_data:
            # no input data for this activity type
            continue
        d_in = input_data[col]
        # set new names for the curves
        d_val.name = "Validation"
        d_in.name = "Input"
        joined = pd.concat([validation_data[col], input_data[col]], axis=1)
        data_sets[col] = joined
    return data_sets


def stacked_prob_curves(filepath: Path | None, area: bool = True):
    if filepath is None or not filepath.is_file():
        return replacement_text()
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
    return [dcc.Graph(figure=figure)]


def prob_curve_per_activity(profile_type_str: str, subdir: str):
    profile_type = data_utils.ptype_from_label(profile_type_str)
    path_val = data_utils.get_file_path(
        datapaths.validation_path / subdir, profile_type
    )
    path_in = data_utils.get_file_path(datapaths.input_data_path / subdir, profile_type)
    if path_val is None or path_in is None:
        return replacement_text()
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
        figures[activity] = figure
        # fill the areas between the curves and the x-axis
        figure.update_traces(fill="tonexty", selector={"name": "Validation"})
        figure.update_traces(fill="tozeroy", selector={"name": "Input"})
        # make the y-axis range symmetric
        max_y = data.abs().max(axis=None)
        figure.update_yaxes(range=[-max_y, max_y])
    # embed the plots in cards
    plots = [
        dbc.Card(
            dbc.CardBody(
                children=[
                    html.H3(activity.title(), style={"textAlign": "center"}),
                    dcc.Graph(figure=fig),
                ]
            )
        )
        for activity, fig in figures.items()  # data_per_activity.items()
    ]
    return plots
