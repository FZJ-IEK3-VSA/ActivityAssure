from activityassure.hetus_data_processing import hetus_constants
from activityassure import validation_statistics


def apply_eurostat_requirements(validation_set: validation_statistics.ValidationSet):
    """
    Applies the data protection requirements from Eurostat by removing too small
    categories and hiding the exact size of some others. Works inplace.

    :param statistics_set: the validation data set to apply the rules to
    """
    validation_set.filter_categories(hetus_constants.MIN_CELL_SIZE)
    size_ranges = [
        hetus_constants.MIN_CELL_SIZE,
        hetus_constants.MIN_CELL_SIZE_FOR_SIZE,
    ]
    validation_set.hide_small_category_sizes(size_ranges)
