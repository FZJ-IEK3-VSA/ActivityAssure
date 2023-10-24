from datetime import datetime, timedelta
from pathlib import Path
from dash import Dash, html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
from activity_validator.hetus_data_processing import activity_profile
from activity_validator.hetus_data_processing.activity_profile import ProfileType

from activity_validator.ui.probability_curves import (
    AIOSelectableProbabilityCurves,
    get_profile_types,
)

df = pd.read_csv(
    "https://raw.githubusercontent.com/plotly/datasets/master/gapminder_unfiltered.csv"
)

# app = Dash(__name__)
app = Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])

# default data paths
validation_path = Path("data/validation")
input_data_path = Path("data/lpg/results")

# data subdirectories
prob_dir = "probability_profiles"
freq_dir = "activity_frequencies"
duration_dir = "activity_durations"
metrics_dir = "metrics"


app.layout = html.Div(
    [
        html.H1(children="Activity Profile Validator", style={"textAlign": "center"}),
        tabs := dcc.Tabs(
            [
                dcc.Tab(label="Validation", value="tab-1-validation"),
                dcc.Tab(label="Input Overview", value="tab-2-overview"),
            ],
            value="tab-1-validation",
        ),
        tab_content := html.Div(id="tabs-content"),
    ]
)


def draw_figure(profile_type: ProfileType):
    # TODO: duplicate code (copied from probability_curves.py)
    # load the appropriate file depending on the profile type
    filename = profile_type.construct_filename("prob") + ".csv"
    _, data = activity_profile.load_df(validation_path / prob_dir / filename)

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
                        html.Div(" - ".join(profile_type.to_tuple())),
                        dcc.Graph(
                            figure=fig,
                            config={"displayModeBar": False},
                        ),
                    ]
                )
            ),
        ]
    )


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


@callback(Output(tab_content, "children"), Input(tabs, "value"))
def render_content(tab):
    if tab == "tab-1-validation":
        return html.Div(
            [
                html.Div(
                    [
                        html.H2("Validation Data"),
                        AIOSelectableProbabilityCurves(validation_path / prob_dir),
                    ]
                ),
                html.Div(
                    [
                        html.H2("Input Data"),
                        AIOSelectableProbabilityCurves(input_data_path / prob_dir),
                    ]
                ),
            ]
        )
    elif tab == "tab-2-overview":
        profile_types = get_profile_types(validation_path / prob_dir)
        graphs = [draw_figure(p) for p in profile_types]

        horizontal_limit = 3
        rows_it = chunks(graphs, horizontal_limit)

        return html.Div(
            dbc.Card(
                dbc.CardBody(
                    [
                        dbc.Row(
                            [dbc.Col([g], width=3) for g in row] + [html.Br()],
                            align="center",
                            justify="center",
                        )
                        for row in rows_it
                    ]
                )
            )
        )
    assert False, f"Unsupported tab name: {tab}"


if __name__ == "__main__":
    app.run(debug=True)
