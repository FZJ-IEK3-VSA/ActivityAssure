from datetime import datetime, timedelta
from pathlib import Path
from dash import Dash, html, dcc, callback, Output, Input
import plotly.express as px
import pandas as pd
from activity_validator.hetus_data_processing import activity_profile

from activity_validator.hetus_data_processing.activity_profile import ProfileType
from activity_validator.ui.probability_curves import AIOSelectableProbabilityCurves

df = pd.read_csv(
    "https://raw.githubusercontent.com/plotly/datasets/master/gapminder_unfiltered.csv"
)

app = Dash(__name__)

validation_path = Path("data/validation")
input_data_path = Path("data/lpg/results")

prob_dir = "probability_profiles"


app.layout = html.Div(
    [
        html.H1(children="Activity Profile Validator", style={"textAlign": "center"}),
        AIOSelectableProbabilityCurves(validation_path / prob_dir),
        AIOSelectableProbabilityCurves(input_data_path / prob_dir),
    ]
)


if __name__ == "__main__":
    app.run(debug=True)
