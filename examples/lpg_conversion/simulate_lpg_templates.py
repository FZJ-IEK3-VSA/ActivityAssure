"""
Start simulation of all LPG templates the desired number of times and store the
results for preprocessing.
"""

from pathlib import Path
import time
import utspclient
from utspclient.datastructures import TimeSeriesRequest
from utspclient.helpers.lpgdata import (
    HouseholdTemplates,
    HouseTypes,
    CalcOption,
)

# create basic LPG calculation config
simulation_config = utspclient.helpers.lpg_helper.create_empty_calcspec(
    HouseTypes.HT23_No_Infrastructure_at_all,
    "2023-01-01",
    "2024-01-01",
    "00:01:00",
    calc_options=[CalcOption.ActionEntries],
)
assert simulation_config.House is not None

# Define connection parameters
address = "134.94.131.167:443"
REQUEST_URL = f"http://{address}/api/v1/profilerequest"
API_KEY = "OrjpZY93BcNWw8lKaMp0BEchbCc"
print(f"UTSP-Server: {address}")

# Define templates to simulate
result_file = "Results.HH1.sqlite"
templates = [HouseholdTemplates.CHR01_Couple_both_at_Work]
templates = [v for k, v in vars(HouseholdTemplates).items() if not k.startswith("__")]
repetitions_per_hh = 1  # 50

template_guids_and_requests = []
for template in templates:
    hhdata = utspclient.helpers.lpg_helper.create_hhdata_from_template(template)
    simulation_config.House.Households = [hhdata]
    template_id = template.split(" ")[0]
    # create simulation ID and request object for each run and store as
    # list of tuples
    new_ids_and_requests = [
        (
            template_id,
            i,
            TimeSeriesRequest(
                simulation_config.to_json(),  # type: ignore
                "LPG",
                guid=f"{i}",
                required_result_files=dict.fromkeys([result_file]),
            ),
        )
        for i in range(repetitions_per_hh)
    ]
    template_guids_and_requests.extend(new_ids_and_requests)

template_names, guids, requests = zip(*template_guids_and_requests)
start = time.time()
results = utspclient.calculate_multiple_requests(
    REQUEST_URL, requests, API_KEY, raise_exceptions=False
)
d = round(time.time() - start, 2)
print(f"Calculation of {len(new_ids_and_requests)} requests took {d} sec.")

# save all result files
base_result_path = Path("data/lpg/raw")
errors_path = base_result_path / "errors"
errors_path.mkdir(parents=True, exist_ok=True)
for template, guid, request, result in zip(template_names, guids, requests, results):
    filename = f"{template}_{request.guid}.sqlite"
    # check if the calculation failed
    if isinstance(result, Exception):
        # write the exception to file in a dedicated errors directory
        filepath = errors_path / f"{template}_{request.guid}_error.txt"
        with open(filepath, "w") as f:
            f.write(str(result))
    else:
        # write the results to file
        result_path = base_result_path / template
        result_path.mkdir(parents=True, exist_ok=True)
        file_content = result.data[result_file]
        filepath = result_path / filename
        with open(filepath, "wb") as f:
            f.write(file_content)
