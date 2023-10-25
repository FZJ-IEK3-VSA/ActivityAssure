from datetime import datetime, timedelta
from pathlib import Path
from dash import Dash, html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
import pandas as pd
from activity_validator.hetus_data_processing import activity_profile
from activity_validator.hetus_data_processing.activity_profile import ProfileType
from activity_validator.ui.overview import draw_figure

from activity_validator.ui.probability_curves import (
    AIOSelectableProbabilityCurves,
    get_profile_types,
)

app = Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])

# default data paths
validation_path = Path("data/validation")
input_data_path = Path("data/lpg/results")

# data subdirectories
prob_dir = "probability_profiles"
freq_dir = "activity_frequencies"
duration_dir = "activity_durations"
metrics_dir = "metrics"


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


# get available validation profile types
profile_types = get_profile_types(validation_path / prob_dir)

tab1_content = html.Div(
    [
        html.Div(
            [
                html.H2("Validation Data", style={"textAlign": "center"}),
                AIOSelectableProbabilityCurves(validation_path / prob_dir),
            ]
        ),
        html.Div(
            [
                html.H2("Input Data", style={"textAlign": "center"}),
                AIOSelectableProbabilityCurves(input_data_path / prob_dir),
            ]
        ),
    ]
)

horizontal_limit = 4
tab2_content = html.Div(
    dbc.Card(
        dbc.CardBody(
            [
                dbc.Row(
                    [
                        dbc.Col([draw_figure(p, validation_path / prob_dir)], width=3)
                        for p in row
                    ]
                    + [html.Br()],
                    align="center",
                    justify="center",
                )
                for row in chunks(profile_types, horizontal_limit)
            ]
        )
    )
)


app.layout = html.Div(
    [
        html.H1(children="Activity Profile Validator", style={"textAlign": "center"}),
        tabs := dcc.Tabs(
            [
                dcc.Tab(tab1_content, label="Validation"),
                dcc.Tab(tab2_content, label="Input Overview"),
            ],
            # value=tab1_content,
        ),
    ]
)


if __name__ == "__main__":
    app.run(debug=True)
