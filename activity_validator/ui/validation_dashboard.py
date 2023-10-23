from pathlib import Path
from dash import Dash, html, dcc, callback, Output, Input
import plotly.express as px
import pandas as pd
from activity_validator.hetus_data_processing import activity_profile

from activity_validator.hetus_data_processing.activity_profile import ProfileType

df = pd.read_csv(
    "https://raw.githubusercontent.com/plotly/datasets/master/gapminder_unfiltered.csv"
)

app = Dash(__name__)

validation_path = Path("data/validation")
input_data_path = Path("data/lpg/results")


app.layout = html.Div(
    [
        html.H1(children="Title of Dash App", style={"textAlign": "center"}),
        dcc.Dropdown(df.country.unique(), "Canada", id="dropdown-selection"),
        dcc.Graph(id="graph-content"),
    ]
)
df = px.data.gapminder()


@callback(Output("graph-content", "figure"), Input("dropdown-selection", "value"))
def update_graph(value):
    # path = ProfileType.from_iterable(profile_type)
    base_path = validation_path / "probability_profiles"
    filename = "prob_DE_female_full time_no work.csv"
    _, df = activity_profile.load_df(base_path / filename)
    df = df.T

    fig = px.area(
        df,
        x=list(range(len(df))),
        y=df.columns,
    )
    # fig.show()
    return fig


if __name__ == "__main__":
    app.run(debug=True)
