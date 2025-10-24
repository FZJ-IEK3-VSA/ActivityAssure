"""Analyze achievable speedup through parallelization in different parts of the
city simulation"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import seaborn as sns


# Convert time strings (hh:mm:ss.ssssss) to total seconds
def to_seconds(t):
    h, m, s = map(float, t.split(":"))
    return h * 3600 + m * 60 + s


# Remark: the speedup test and this plot are done in style of Amdahl's law
# I could also try another test according to Gustafson's law, i.e. start
# different runs with increasing size AND number of workers, keeping the
# ratio of houses per worker constant.

sns.set_theme()

# file with combined outputs of the speedtest
csv_path = Path("R:/phd_dir/results/speedtest100/speedtest.csv")
df = pd.read_csv(csv_path)

for col in ["Initialization", "Main Simulation", "Postprocessing"]:
    df[col] = df[col].apply(to_seconds)

# Plot processing times over number of workers
plt.figure(figsize=(8, 5))
plt.plot(df["Workers"], df["Initialization"], marker="o", label="Initialization")
plt.plot(df["Workers"], df["Main Simulation"], marker="o", label="Main Simulation")
plt.plot(df["Workers"], df["Postprocessing"], marker="o", label="Postprocessing")

plt.xlabel("Number of Workers")
plt.ylabel("Time [s]")
plt.legend()
plt.grid(True)
plt.tight_layout()
# plt.show()
plt.savefig("parallel_speedup.svg")
