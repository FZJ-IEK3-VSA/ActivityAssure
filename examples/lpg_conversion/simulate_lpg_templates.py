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
repetitions_per_hh = 1  # 100

# TODO: check which result files are already there, and only request the missing files
all_requests = []
all_templates = []
for template in templates:
    print(f"--- Sending requests for template {template} ---")
    hhdata = utspclient.helpers.lpg_helper.create_hhdata_from_template(template)
    simulation_config.House.Households = [hhdata]
    requests = [
        TimeSeriesRequest(
            simulation_config.to_json(),  # type: ignore
            "LPG",
            guid=f"{i}",
            required_result_files=dict.fromkeys([result_file]),
        )
        for i in range(repetitions_per_hh)
    ]
    # TODO: temporary solution
    all_requests.extend(requests)
    all_templates.extend([template] * len(requests))

requests = all_requests

start = time.time()
results = utspclient.calculate_multiple_requests(REQUEST_URL, requests, API_KEY)
d = round(time.time() - start, 2)
print(f"Calculation of {len(requests)} requests took {d} sec.")

# save all result files
base_result_path = Path("data/lpg/raw")
for template, request, result in zip(all_templates, requests, results):
    assert not isinstance(result, Exception)
    file_content = result.data[result_file]
    short_name = template.split(" ")[0]
    result_path = base_result_path / short_name
    result_path.mkdir(parents=True, exist_ok=True)
    filename = result_path / f"{short_name}_{request.guid}.sqlite"
    with open(filename, "wb") as f:
        f.write(file_content)
