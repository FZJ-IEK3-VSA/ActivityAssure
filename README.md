# Activity Validator

The Activity Validator is a validation framework for activity profiles and behavior models that generate them. For proper usage, a validation data set is required, which is available [on Zenodo]().
The concept of the framework is to categorize activity profiles by country, sex, employment status, and day type, calculate statistics for each category, and then compare activity statistics from the same categories.

The framework provides modules for preprocessing and categorizing activity profiles, and for comparing them to the statistics of the validation data set. For the latter, a Dash web application is provided that shows interactive comparison plots and indicators to individually assess each category.

The [hetus_data_processing](activity_validator/hetus_data_processing) subpackage contains the code that was used to generate the aforementioned validation data set from the HETUS 2010 time use survey.

## Installation
To set up the Activity Validator for usage, clone this repository and install it, e.g. with pip:

    pip install .

Next, download the [activity validation data set]() and extract it, for example to a ```data/validation_data_sets``` subdirectory within the main repository directory.

## Validating a Model
To validate activity profiles from a model, you need to provide the input profiles in csv format, and an activity mapping and a person characteristics file in json format. Optionally, an activity merging file can be specified.

Each input profile needs to have at least two columns: 'Timestep', which contains the simulation timestep (the temporal resolution used must be specified later), and 'Activity', which is a string that denotes the activity of the person at that timestep. Each file only contains the profile for a single person, but it may arbitrarily long. However, only full days will be processed. By default, the profile is assumed to start at 00:00 o'clock. If it does not, an additional 'Date' column with ISO8601 timestamps may be specified, from which the starting time will then be read. All input profiles must be located in a single directory, and adhere to the following naming scheme: ```personid_number.csv```.
```personid``` must be a unique identifier for the person, that means your model configuration which produced the activity profile. It can be anything, but it must be unique. Optionally, any free text can be added, which can be used to distinguish between multiple profiles from the same person. If used, it must be delimited by a single underscore ```_```.

The person characteristics file contains the necessary categorization attributes for each of your persons. That means, for each person, the person ID must be mapped to the corresponding sex, employment status and country. The person IDs in this file must match those in the filenames of the csv data files. Possible values for each of the categorization attributes can be found in [categorization_attributes.py](activity_validator/categorization_attributes.py). For the country, the [two-letter codes from Eurostat](https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Glossary:Country_codes) are used.

The activity mapping is a dictionary that maps each custom activity from your model to one of the 15 activities used in the framework. The available activities can be seen in the ```activities``` subdirectory of the validation data set.

The optional activity merging file can be used when the model cannot make use of all 15 activities used by the framework, for example, if 'laundry' and 'clean' are modelled as a single activity. In that case, the corresponding statistics in the validation data set have to be merged. For that, the merging file defines the mapping to use. It has the same format as the activity mapping file, but it maps the activity names of the framework to a new name that you can choose. In particular assigning multiple activities to the same new name is possible and leads to merging.

Examples for the format of each of these files can be found in the LoadProfileGenerator example, in the [data subdirectory](examples/LoadProfileGenerator/data).

When all files are prepared in the correct format, it is best to start with a copy of the LoadProfileGenerator example and simply enter your own paths. Then just execute the main example script.

## Running an Example
The [LoadProfileGenerator](examples/LoadProfileGenerator) example demonstrates usage of the framework by validating the [LoadProfileGenerator](https://www.loadprofilegenerator.de/), an activity-based model for generating residential load profiles. The example data set is the preprocessed output of a simulation with the LoadProfileGenerator.
To run the example, set the correct path to the validation data set in [example_lpg_validation.py](examples/LoadProfileGenerator/example_lpg_validation.py) and execute this file. This should generate activity statistics for the LoadProfileGenerator data, as well as comparison indicators for evaluating its similarity to the validation data.

## Running the Dash web app
To run the interactive Dash validation web app, set the correct paths to the valdiation data set and your model statistics data set in [datapaths.py](activity_validator/ui/datapaths.py). Then execute the following command:

    python activity_validator/ui/validation_dashboard.py

This will start the app with the Dash development server (which should be enough for local usage). The server will print the address where the web app is available (e.g., http://127.0.0.1:8050/). Open the URL in a browser to access the validation app.