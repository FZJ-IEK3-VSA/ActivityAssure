import os
import pandas as pd

DATA_DIR = "data"
STATISTICS_DIR = os.path.join(DATA_DIR, "eurostat")


def read_stat_data(filename: str):
    path = os.path.join(STATISTICS_DIR, filename)
    data = pd.read_csv(path, sep=",", parse_dates=[1])
    print(data.head())
    print(data["geo"].value_counts())


if __name__ == "__main__":
    filename = "tus_00age_linear.csv"
    read_stat_data(filename)
