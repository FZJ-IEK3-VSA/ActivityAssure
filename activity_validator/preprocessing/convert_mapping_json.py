import json


path = r"activity_validator\activity_types\hetus_list.json"
with open(path) as f:
    data = json.load(f)

# path = r"activity_validator\activity_types\activities.json"
# with open(path) as f:
#     data2 = json.load(f)

result = {k: None for k in data}

# result = {}
# for author, a_old in data.items():
#     a_new = data2[author]
#     assert len(a_old) == len(a_new)
#     d = {o: n for o, n in zip(a_old, a_new)}
#     result[author] = d


result_path = r"activity_validator\activity_types\mapping_hetus.json"
with open(result_path, "w+", encoding="utf-8") as f:
    json.dump(result, f, indent=4)
