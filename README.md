# Activity Validator

The Activity Validator is a validation framework for activity profiles and behavior models that generate them. For proper usage, a validation data set is required, which is available [on Zenodo]().
The concept of the framework is to categorize activity profiles by country, sex, employment status, and day type, calculate statistics for each category, and then compare activity statistics from the same categories.

The framework provides modules for preprocessing and categorizing activity profiles, and for comparing them to the statistics of the validation data set. For the latter, a Dash web application is provided that shows interactive comparison plots and indicators to individually assess each category.

The [hetus_data_processing](activity_validator/hetus_data_processing) subpackage contains the code that was used to generate the aforementioned validation data set from the HETUS 2010 time use survey.

## Installation
To set up the Activity Validator for usage, clone this repository and install it, e.g. with pip:

    pip install .

Next, download the [activity validation data set]() and extract it, for example to a ```data``` subdirectory within the main repository directory.

## Running an Example
The [LoadProfileGenerator](examples/LoadProfileGenerator) example demonstrates usage of the framework by validating the [LoadProfileGenerator](https://www.loadprofilegenerator.de/), an activity-based model for generating residential load profiles. The example data set is the preprocessed output of a simulation with the LoadProfileGenerator.
To run the example, set the correct path to the validation data set in [example_lpg_validation.py](examples/LoadProfileGenerator/example_lpg_validation.py) and execute this file. This should generate activity statistics for the LoadProfileGenerator data, as well as comparison indicators for evaluating its similarity to the validation data.

## Running the Dash web app
To run the interactive Dash validation web app, execute the following:

    python activity_validator/ui/validation_dashboard.py

This will start the app with the Dash development server (which should be enough for local usage). The server will print the address where the web app is available (e.g., http://127.0.0.1:8050/). Open the URL in a browser to access the validation app.