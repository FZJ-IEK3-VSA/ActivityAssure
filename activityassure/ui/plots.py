from datetime import datetime, timedelta
import math
from pathlib import Path
from dash import html, dcc  # type: ignore
import dash_bootstrap_components as dbc  # type: ignore
import plotly.express as px  # type: ignore
import plotly.graph_objects as go  # type: ignore
from plotly.graph_objects import Figure  # type: ignore
import pandas as pd

from activityassure.ui.config import config
from activityassure.hetus_data_processing import (
    hetus_constants,
)
from activityassure import (
    pandas_utils,
    profile_category,
    validation_statistics,
    comparison_indicators,
)
from activityassure.ui import data_utils, datapaths
from activityassure.ui import translation
from activityassure.ui.translation import UIText


# workaround for an unresolved bug that randomly causes exceptions
# on initial app launch: https://github.com/plotly/plotly.py/issues/3441
go.Figure(layout=dict(template="plotly"))


# general config for all plots
GLOBAL_GRAPH_CONFIG: dcc.Graph.Config = {
    "toImageButtonOptions": {
        "format": "svg",  # one of png, svg, jpeg, webp
        # "filename": "custom_image",
    }
}
# font settings for all plots
GLOBAL_FONT = {
    "size": 16,
}
# height for the stacked and difference pltos
STACKED_HEIGHT = 500

# defines the color scheme for plots which show multiple ativities
STACKED_PROB_CURVE_COLOR = px.colors.qualitative.Plotly + px.colors.qualitative.Set1

# defines a sensible default order of activities for plots which show multiple ativities
_DEFAULT_ACTIVITY_ORDER = [
    "sleep",
    "work",
    "other",
    "tv",
    "eat",
    "not at home",
    "personal care",
    "cook",
    "clean",
    "pc",
    "dishwashing",
    "education",
    "iron",
    "laundry",
    "radio/music",
]
# determine the global activity order to use for all plots
ACTIVITY_ORDER = data_utils.get_final_activity_order(
    datapaths.validation_path, datapaths.input_data_path, _DEFAULT_ACTIVITY_ORDER
)


def replacement_text(text: str = translation.get(UIText.no_data_available)):
    """
    Function to generate a default replacement text for when
    the data to display is missing.

    :param text: the text to display, defaults to "No data available"
    :return: the display element
    """
    return html.Div(children=[text], style={"textAlign": "center"})


def titled_card(content, title: str = "", **kwargs) -> dbc.Card:
    """
    Embeds any content in a card with an optional title.
    Additional keyword arguments are passed to the Card
    constructor.

    :param content: content for the card
    :param title: title for the card
    :return: the resulting Card object
    """
    if not isinstance(content, list):
        content = [content]
    t = [html.H3(title, style={"textAlign": "center"})] if title else []
    return dbc.Card(dbc.CardBody(children=t + content), **kwargs)


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
    columns = set(validation_data.columns) | set(input_data.columns)
    for col in columns:
        # get the respective columns, if they exist
        d_val, d_in, dtype = None, None, None
        if col in validation_data:
            d_val = validation_data[col]
            dtype = d_val.dtype
        if col in input_data:
            d_in = input_data[col]
            dtype = d_in.dtype
        assert dtype, "No dtype found, this should not happen"
        if d_val is None:
            # no validation data for this activity type: create an empty column
            d_val = pd.Series([], dtype=dtype)
        if d_in is None:
            # no input data for this activity type: create an empty column
            d_in = pd.Series([], dtype=dtype)
        # set new names for the curves
        d_val.name = config.validation_name
        d_in.name = config.model_name
        joined = pd.concat([d_val, d_in], axis=1)
        data_sets[col] = joined
    return data_sets


def remove_trailing_zero_rows(data: pd.DataFrame) -> pd.DataFrame:
    """
    Finds the last row that contains at least one non-zero value, and
    removes all subsequent rows. Can be used for cleaning data for
    bar charts, for example.

    :param data: input DataFrame with zero rows
    :return: DataFrame with last rows removed
    """
    # convert nan to 0 first
    data.fillna(0, inplace=True)
    # find the last non-zero row
    last_nonzero_row = (data != 0).any(axis=1).cumsum().idxmax()
    last_nonzero_position = data.index.get_loc(last_nonzero_row)
    assert isinstance(last_nonzero_position, int), "Unexpected index type"
    # cut off the last zero-rows
    return data.iloc[: last_nonzero_position + 1]


def stacked_prob_curves(filepath: Path | None) -> Figure | None:
    if filepath is None or not filepath.is_file():
        return None
    # load the correct file
    data = pandas_utils.load_df(filepath)
    # transpose data for plotting
    data = data.T
    data = data_utils.reorder_activities(data, ACTIVITY_ORDER)
    time_values = get_date_range(len(data))
    # plot the data
    fig = px.area(
        data,
        x=time_values,
        y=data.columns,
        color_discrete_sequence=STACKED_PROB_CURVE_COLOR,
    )
    fig.update_xaxes(tickformat="%H:%M")  # pyright: ignore[reportAttributeAccessIssue]
    fig.update_layout(
        title=translation.get(UIText.stacked_prob_curves),
        xaxis_title=translation.get(UIText.time),
        yaxis_title=translation.get(UIText.probability),
        height=STACKED_HEIGHT,
        font=GLOBAL_FONT,
        legend_title_text=translation.get(UIText.activities),
    )
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
        translation.get(UIText.prob_profiles),
        name=(
            config.validation_name
            if "valid" in str(directory).lower()
            else config.model_name
        ),
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
    data_val = pandas_utils.load_df(path_valid)
    data_in = pandas_utils.load_df(path_in)

    # get the probability profile differences
    data_val, data_in = comparison_indicators.make_probability_dfs_compatible(
        data_val, data_in
    )
    diff = comparison_indicators.calc_probability_curves_diff(data_val, data_in)
    diff = diff.T
    diff = data_utils.reorder_activities(diff, ACTIVITY_ORDER)
    time_values = get_date_range(len(diff))
    # plot the data
    fig = px.line(
        diff,
        x=time_values,
        y=diff.columns,
        color_discrete_sequence=STACKED_PROB_CURVE_COLOR,
    )
    fig.update_xaxes(tickformat="%H:%M")  # pyright: ignore[reportAttributeAccessIssue]
    fig.update_layout(
        title=translation.get(
            UIText.prob_curve_diff, config.model_name, config.validation_name
        ),
        xaxis_title=translation.get(UIText.time),
        yaxis_title=translation.get(UIText.prob_diff),
        height=STACKED_HEIGHT,
        font=GLOBAL_FONT,
        legend_title_text=translation.get(UIText.activities),
    )
    return fig


def prob_curve_per_activity(
    profile_type_val: profile_category.ProfileCategory,
    profile_type_in: profile_category.ProfileCategory,
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
    validation_data = pandas_utils.load_df(path_val)
    input_data = pandas_utils.load_df(path_in)

    # make sure the data is compatible for plotting
    validation_data, input_data = comparison_indicators.make_probability_dfs_compatible(
        validation_data, input_data
    )

    # assign time values for the timesteps
    time_values = get_date_range(len(validation_data.columns))
    validation_data.columns = time_values
    input_data.columns = time_values
    # determine common index with all activity types
    common_index = validation_data.index.union(input_data.index)
    # add rows full of zeros for missing activity types
    validation_data = validation_data.reindex(common_index, fill_value=0)
    input_data = input_data.reindex(common_index, fill_value=0)
    # check if the validation data should be mirrored on the x axis
    val_factor = -1 if config.mirrored_plots else 1
    validation_data = validation_data.T * val_factor
    input_data = input_data.T
    data_per_activity = join_to_pairs(validation_data, input_data)
    # define tick values and labels
    if config.mirrored_plots:
        # mirrored plot: remove sign for negative tick labels
        tickvals = [-1, -0.5, 0, 0.5, 1]
        ticklabels = [abs(x) for x in tickvals]
        min_yval = -1
    else:
        # let plotly set ticks automatically
        tickvals = None
        ticklabels = None
        min_yval = 0

    # create the plots
    figures = {}
    for activity, data in data_per_activity.items():
        figure = px.line(data)
        # fill the areas between the curves and the x-axis
        figure.update_traces(fill="tozeroy", selector={"name": config.model_name})
        figure.update_traces(fill="tozeroy", selector={"name": config.validation_name})
        # use the same y-axis range for all plots
        figure.update_yaxes(  # pyright: ignore[reportAttributeAccessIssue]
            range=[min_yval, 1]
        )
        figure.update_xaxes(  # pyright: ignore[reportAttributeAccessIssue]
            tickformat="%H:%M"
        )
        # set title and axis labels
        figure.update_layout(
            title=translation.get(UIText.activity_prob, activity),
            xaxis_title=translation.get(UIText.time),
            yaxis=dict(
                title=translation.get(UIText.probability),
                tickmode="array",
                tickvals=tickvals,
                ticktext=ticklabels,
            ),
            font=GLOBAL_FONT,
            legend_title_text="",
            showlegend=config.show_legend_per_activity,
        )
        figures[activity] = dcc.Graph(figure=figure, config=GLOBAL_GRAPH_CONFIG)
    return figures


def histogram_per_activity(
    ptype_val: profile_category.ProfileCategory,
    ptype_in: profile_category.ProfileCategory,
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
    validation_data = pandas_utils.load_df(path_val, duration_data)
    input_data = pandas_utils.load_df(path_in, duration_data)
    if duration_data:
        # workaround for getting a timedelta axis
        # https://github.com/plotly/plotly.py/issues/799
        validation_data.index += datetime(2023, 1, 1)
        input_data.index += datetime(2023, 1, 1)
        title = translation.get(UIText.activity_durations)
        xaxis_title = translation.get(UIText.activity_duration)
    else:
        title = translation.get(UIText.activity_freq)
        xaxis_title = translation.get(UIText.activity_reps_per_day)

    data_per_activity = join_to_pairs(validation_data, input_data)

    # remove trailing zero rows to make the histograms cleaner
    for a, df in data_per_activity.items():
        data_per_activity[a] = remove_trailing_zero_rows(df)

    # create the plot for each activity
    figures = {
        activity: px.bar(d, barmode="overlay")
        for activity, d in data_per_activity.items()
    }
    # set title, axis lables and tick format, if necessary
    for a, f in figures.items():
        f.update_layout(
            title=f'"{a}" {title}',
            xaxis_title=xaxis_title,
            yaxis_title=translation.get(UIText.probability),
            font=GLOBAL_FONT,
            legend_title_text="",
            showlegend=config.show_legend_per_activity,
        )
        if duration_data:
            # set the correct format so only the time is shown, and not the date
            f.update_xaxes(  # pyright: ignore[reportAttributeAccessIssue]
                tickformat="%H:%M"
            )
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
    datasets = {k: pandas_utils.load_df(path) for k, path in paths.items()}
    # calculate the average probabilities per profile type
    data = pd.DataFrame({title: data.mean(axis=1) for title, data in datasets.items()})
    # add the overall probabilities
    data[translation.get(UIText.overall)] = data.mean(axis=1)
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
        formatted_str = translation.get(UIText.days, days, formatted_str)
    return formatted_str


def timedelta_to_str(t: timedelta) -> str:
    # python's default representation of negative timedeltas is unintuitive
    if t < timedelta(0):
        sign = "-"
        t *= -1
    else:
        sign = ""
    return sign + format_timedelta(t)


def indicator_as_time_str(value: float) -> str:
    """
    Converts an indicator from a float in range [-1, 1] to
    a str representation of a timedelta in range [-1 day, 1 day].
    This helps to understand the meaning of indicators like mae
    and bias.

    :param value: bias value
    :return: str timedelta representation
    """
    if not math.isfinite(value):
        return "Nan/Inf"
    td = timedelta(value)
    return timedelta_to_str(td)


def get_all_indicator_variants(
    ptype_val: profile_category.ProfileCategory,
    ptype_in: profile_category.ProfileCategory,
    add_means: bool,
) -> tuple[
    comparison_indicators.ValidationIndicators,
    comparison_indicators.ValidationIndicators,
    comparison_indicators.ValidationIndicators,
]:
    """
    Loads the statistics for validation and input data and calculates
    validation indicators in all variants.

    :param ptype_val: the selected profile type of the validation data
    :param ptype_in: the selected profile type of the input data
    :param add_means: if True, adds indicator means across all activities
    :raises RuntimeError: when statistics for a profile type could not be loaded
    :return: tuple of validation indicators
    """
    # load the statistics for validation and input data
    data_val = validation_statistics.ValidationStatistics.load(
        datapaths.validation_path, ptype_val
    )
    data_in = validation_statistics.ValidationStatistics.load(
        datapaths.input_data_path, ptype_in
    )
    # calculate the indicators without saving them to file
    _, metrics, scaled, normed = comparison_indicators.calc_all_indicator_variants(
        data_val, data_in, False, add_means=add_means
    )
    return metrics, scaled, normed


def indicator_table_rows(
    indicators: comparison_indicators.ValidationIndicators,
    activity: str,
    title: str = "",
    extended: bool = True,
):
    """
    Creates indicator tables rows for one activity, for
    a single indicator variant (default/scaled/normed)

    :param indicators: the indicator object (any variant)
    :param activity: the activity name (only used to get indicator values)
    :param title: title for the table rows (should match the variant), defaults to ""
    :param extended: if True, the full set of indicators is shown, else only the indicators
                     which are affected by scaling/norming, defaults to True
    :return: indicator table rows
    """
    digits = 6
    bold = {"fontWeight": "bold"}
    title_rows = [html.Tr([html.Td(title)], style=bold)] if title else []
    basic_rows = [
        html.Tr(
            [
                html.Td(translation.get(UIText.mae_time)),
                html.Td(indicator_as_time_str(indicators.mae[activity])),
            ]
        ),
        html.Tr(
            [
                html.Td(translation.get(UIText.bias_time)),
                html.Td(indicator_as_time_str((indicators.bias[activity]))),
            ]
        ),
        html.Tr(
            [
                html.Td(translation.get(UIText.rmse)),
                html.Td(round_kpi(indicators.rmse[activity] ** 2, digits)),
            ]
        ),
        html.Tr(
            [
                html.Td(translation.get(UIText.wasserstein_dist)),
                html.Td(round_kpi(indicators.wasserstein[activity], digits)),
            ]
        ),
    ]
    if extended:
        extended_rows = [
            html.Tr(
                [
                    html.Td(translation.get(UIText.pearson_corr)),
                    html.Td(round_kpi(indicators.pearson_corr[activity], digits)),
                ]
            )
        ]
    else:
        extended_rows = []
    return title_rows + basic_rows + extended_rows


def create_indicator_table(
    indicators: comparison_indicators.ValidationIndicators,
    scaled_indicators: comparison_indicators.ValidationIndicators,
    normed_indicators: comparison_indicators.ValidationIndicators,
    activity: str,
) -> dbc.Table:
    """
    Creates an indicator table for one activity, with sections for each
    indicator variant.

    :param indicators: default indicators
    :param scaled_indicators: scaled indicators
    :param normed_indicators: normed indicators
    :param activity: the activity name (only used to get indicator values)
    :return: indicator table for one activity
    """
    return dbc.Table(
        indicator_table_rows(
            indicators, activity, translation.get(UIText.prob_curves_abs)
        )
        + indicator_table_rows(
            scaled_indicators,
            activity,
            translation.get(UIText.prob_curves_rel),
            False,
        )
        + indicator_table_rows(
            normed_indicators, activity, translation.get(UIText.prob_curves_norm), False
        )
    )


def indicator_tables_per_activity(
    ptype_val: profile_category.ProfileCategory,
    ptype_in: profile_category.ProfileCategory,
) -> dict[str, dbc.Table]:
    """
    Generates an indicator table for each activity.

    :param ptype_val: the selected profile type of the validation data
    :param ptype_in: the selected profile type of the input data
    :return: dict of all KPI tables
    """
    try:
        # get indicators without means
        metrics, scaled, normed = get_all_indicator_variants(ptype_val, ptype_in, False)
    except RuntimeError:
        return {}
    tables = {
        a: create_indicator_table(metrics, scaled, normed, a) for a in metrics.mae.index
    }
    return tables
