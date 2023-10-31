from datetime import datetime, timedelta
from pathlib import Path
from dash import Dash, Output, Input, State, html, dcc, callback, MATCH  # type: ignore
import dash_bootstrap_components as dbc  # type: ignore
import plotly.express as px  # type: ignore
import uuid

import pandas as pd
from activity_validator.hetus_data_processing import activity_profile
from activity_validator.hetus_data_processing.activity_profile import ProfileType
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


def sum_curves_per_activity_type(
    profile_type_str: str, subdir: Path, duration_data: bool = False
):
    """
    Generates a set of histogram plots, one for each activity type.
    Each histogram compares the validation data to the matching input
    data.

    :param profile_type_str: the selected profile type
    :param subdir: the data subdirectory to use, which must contain
                   data per activity type in each file
    :param duration_data: whether to convert the data to timedeltas, defaults to False
    :return: a list of Cards containing the individual plots
    """
    # determine file paths for validation and input data
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
    # convert data if necessary
    if duration_data:
        convert_to_timedelta(validation_data)
        convert_to_timedelta(input_data)

    data_per_activity = join_to_pairs(validation_data, input_data)

    # create the plot for all activity types and wrap them in Cards
    # TODO alternative: use ecdf instead of histogram for a sum curve
    plots = [
        dbc.Card(
            dbc.CardBody(
                children=[
                    html.H3(activity.title(), style={"textAlign": "center"}),
                    dcc.Graph(figure=px.histogram(d, barmode="overlay")),
                ]
            )
        )
        for activity, d in data_per_activity.items()
    ]
    return plots


class MainValidationView(html.Div):
    """
    A reusable component containing a profile category selector
    and a graph showing the corresponding activity probability
    curves.
    """

    class ids:
        # A set of functions that create pattern-matching callbacks of the subcomponents
        # store = lambda aio_id: {
        #     "component": "AIOSelectableProbabilityCurves",
        #     "subcomponent": "store",
        #     "aio_id": aio_id,
        # }
        dropdown = lambda aio_id: {
            "component": "AIOSelectableProbabilityCurves",
            "subcomponent": "dropdown",
            "aio_id": aio_id,
        }
        validation_graph = lambda aio_id: {
            "component": "AIOSelectableProbabilityCurves",
            "subcomponent": "validation probability graph",
            "aio_id": aio_id,
        }
        input_graph = lambda aio_id: {
            "component": "AIOSelectableProbabilityCurves",
            "subcomponent": "input probability graph",
            "aio_id": aio_id,
        }
        difference_graph = lambda aio_id: {
            "component": "AIOSelectableProbabilityCurves",
            "subcomponent": "probability difference graph",
            "aio_id": aio_id,
        }
        per_activity_graphs = lambda aio_id: {
            "component": "AIOSelectableProbabilityCurves",
            "subcomponent": "per activity type graphs",
            "aio_id": aio_id,
        }

    # Define the arguments of the component
    def __init__(
        self,
        dropdown_props=None,
        graph_props=None,
        aio_id=None,
    ):
        """
        - `aio_id` - The All-in-One component ID used to generate the markdown and dropdown components's dictionary IDs.

        The All-in-One component dictionary IDs are available as
        - MarkdownWithColorAIO.ids.dropdown(aio_id)
        - MarkdownWithColorAIO.ids.markdown(aio_id)
        """
        dropdown_props = dropdown_props or {}
        graph_props = graph_props or {}

        if not aio_id:
            # if not set by user, define a random ID
            aio_id = str(uuid.uuid4())

        # get available profile categories
        validation_types = data_utils.get_profile_type_labels(
            datapaths.validation_path / datapaths.prob_dir
        )
        input_types = data_utils.get_profile_type_labels(
            datapaths.input_data_path / datapaths.prob_dir
        )
        all_types = sorted(list(set(validation_types) | set(input_types)))

        # Define the component's layout
        super().__init__(
            [
                # dcc.Store(data=str(validation_path), id=self.ids.store(aio_id)),
                dcc.Dropdown(
                    all_types,
                    input_types[0],
                    id=self.ids.dropdown(aio_id),
                    **dropdown_props,
                ),
                html.Div(
                    [
                        html.H2("Validation Data", style={"textAlign": "center"}),
                        html.Div(id=self.ids.validation_graph(aio_id)),
                    ]
                ),
                html.Div(
                    [
                        html.H2(
                            "LoadProfileGenerator Data", style={"textAlign": "center"}
                        ),
                        html.Div(id=self.ids.input_graph(aio_id)),
                    ]
                ),
                html.Div(
                    [
                        html.H2("Difference", style={"textAlign": "center"}),
                        html.Div(id=self.ids.difference_graph(aio_id)),
                    ]
                ),
                html.Div(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    html.H2(
                                        "Activity Frequencies per Day",
                                        style={"textAlign": "center"},
                                    )
                                ),
                                dbc.Col(
                                    html.H2(
                                        "Activity Durations",
                                        style={"textAlign": "center"},
                                    )
                                ),
                                dbc.Col(
                                    html.H2(
                                        "Activity Probabilities",
                                        style={"textAlign": "center"},
                                    )
                                ),
                            ],
                        ),
                        html.Div(id=self.ids.per_activity_graphs(aio_id)),
                    ]
                ),
            ],
        )

    @callback(
        Output(ids.validation_graph(MATCH), "children"),
        Input(ids.dropdown(MATCH), "value"),
    )
    def update_validation_graph(profile_type_str):
        return update_prob_curves(
            profile_type_str, datapaths.validation_path / datapaths.prob_dir
        )

    @callback(
        Output(ids.input_graph(MATCH), "children"), Input(ids.dropdown(MATCH), "value")
    )
    def update_input_graph(profile_type_str):
        return update_prob_curves(
            profile_type_str, datapaths.input_data_path / datapaths.prob_dir
        )

    @callback(
        Output(ids.difference_graph(MATCH), "children"),
        Input(ids.dropdown(MATCH), "value"),
    )
    def update_diff_graph(profile_type_str):
        return update_prob_curves(
            profile_type_str, datapaths.input_data_path / datapaths.diff_dir, area=False
        )

    @callback(
        Output(ids.per_activity_graphs(MATCH), "children"),
        Input(ids.dropdown(MATCH), "value"),
    )
    def update_activity_dur_graphs(profile_type_str):
        freq = sum_curves_per_activity_type(profile_type_str, datapaths.freq_dir)
        dur = sum_curves_per_activity_type(
            profile_type_str, datapaths.duration_dir, True
        )
        prob = prob_curve_per_activity(profile_type_str, datapaths.prob_dir)
        return dbc.Row([dbc.Col(freq), dbc.Col(dur), dbc.Col(prob)])
