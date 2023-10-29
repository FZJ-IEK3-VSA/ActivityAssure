from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from dash import html, dcc  # type:ignore
import dash_bootstrap_components as dbc  # type:ignore
import plotly.express as px  # type:ignore

from activity_validator.hetus_data_processing import activity_profile
from activity_validator.hetus_data_processing.activity_profile import ProfileType


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def draw_figure(profile_type: ProfileType, path: Path):
    # TODO: duplicate code (copied from probability_curves.py)
    # load the appropriate file depending on the profile type
    filename = profile_type.construct_filename("prob") + ".csv"
    _, data = activity_profile.load_df(path / filename)

    data = data.T

    # generate 24h time range starting at 04:00
    resolution = timedelta(days=1) / len(data)
    start_time = datetime.strptime("04:00", "%H:%M")
    end_time = start_time + timedelta(days=1) - resolution
    time_values = pd.date_range(start_time, end_time, freq=resolution)

    # plot the data
    fig = px.area(
        data,
        x=time_values,
        y=data.columns,
    )
    return html.Div(
        [
            dbc.Card(
                dbc.CardBody(
                    [
                        html.Div(
                            " - ".join(profile_type.to_tuple()),
                            style={"textAlign": "center"},
                        ),
                        dcc.Graph(
                            figure=fig,
                            config={"displayModeBar": False},
                        ),
                    ]
                )
            ),
        ]
    )


def create_rows(path: Path, profile_types, num_columns=4):
    return [
        dbc.Row(
            [dbc.Col([draw_figure(p, path)], width=3) for p in row] + [html.Br()],
            align="center",
            justify="center",
        )
        for row in chunks(profile_types, num_columns)
    ]
