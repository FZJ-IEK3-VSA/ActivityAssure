"""Load travel information from an LPG result database"""

from dataclasses import dataclass
from pathlib import Path

from activityassure.preprocessing.lpg import activity_profiles


@dataclass
class Travel:
    start: int
    duration: int
    start_site: str
    dest_site: str
    distance_in_m: float
    device: str


def load_travels_from_db(database_path: Path) -> list[Travel]:
    # load all activities and TravelRoutes from DB
    action_dicts = activity_profiles.load_lpg_result_table(
        database_path, "PerformedActions"
    )
    route_dicts = activity_profiles.load_lpg_result_table(database_path, "TravelRoutes")
    routes = {r["Name"]: r for r in route_dicts}

    travel_indices = [i for i, d in enumerate(action_dicts) if d["IsTravel"]]
    if travel_indices[-1] == len(action_dicts):
        # drop the last travel if it was the last action, as its duration is unknown
        travel_indices.pop()

    # collect relevant data for each travel
    travels = []
    for i in travel_indices:
        travel = action_dicts[i]
        next_aff = action_dicts[i + 1]
        start = travel["TimeStep"]["ExternalStep"]
        duration = next_aff["TimeStep"]["ExternalStep"] - start
        route_name = travel["Affordancename"].removeprefix("travel on ")

        # get the relevant route object for additional data
        route = routes[route_name]
        start_site = route["SiteAName"]
        dest_site = route["SiteBName"]
        assert len(routes["Steps"]) == 1, "Not implemented for multiple steps yet"
        distance = routes["Steps"]["DistanceInM"]
        device = routes["Steps"]["TransportationDeviceCategory"]["Name"].removesuffix(
            " Category"
        )
        travels.append(Travel(start, duration, start_site, dest_site, distance, device))
    return travels
