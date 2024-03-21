from activity_validator.hetus_data_processing import load_data
from activity_validator.hetus_data_processing import main


def test_validation_data_set_ceation():
    # TODO: use an artificial fake data set instead (not real HETUS)
    HETUS_PATH = "D:/Daten/HETUS Data/HETUS 2010 full set/DATA"
    data = load_data.load_hetus_files(["LU"], HETUS_PATH)
    # reduce data size
    data = data.iloc[:1000]
    result = main.process_hetus_2010_data(data)

    assert result.activities
    assert result.statistics
