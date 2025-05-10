#%% Read validation data
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
country1 = 'AT'
country2 = 'DE'

validation_results_country1 = pd.read_csv(f"../../data/validation/lpg_example/{country1}/validation_results/default/indicators_per_category.csv", index_col=[0,1])
validation_results_country2 = pd.read_csv(f"../../data/validation/lpg_example/{country2}/validation_results/default/indicators_per_category.csv", index_col=[0,1])
validation_results_country1.index = validation_results_country1.index.set_levels(
    validation_results_country1.index.levels[0].str.replace(f"{country1}_", ""), level=0
)
validation_results_country2.index = validation_results_country2.index.set_levels(
    validation_results_country2.index.levels[0].str.replace(f"{country2}_", ""), level=0
)

#%% Calculate deviance by profile and activity
absolute_diff = validation_results_country1.abs() - validation_results_country2.abs() 
relative_diff = absolute_diff / validation_results_country2.abs()

relative_diff = relative_diff[relative_diff.index.get_level_values(1) != 'mean']

fig, ax = plt.subplots(figsize=(4,12))
sns.heatmap(relative_diff, ax=ax)

#%% Plot differences in errors
fig, ax = plt.subplots(figsize=(4,3))
sns.boxplot(relative_diff, ax=ax)
ax.set_ylabel("relative deviance")
ax.set_xticklabels(ax.get_xticklabels(), rotation=45)

#%% Zoom in
fig, ax = plt.subplots(figsize=(4,3))
sns.boxplot(relative_diff, showfliers=False, ax=ax)
ax.set_ylabel("relative deviance")
ax.set_xticklabels(ax.get_xticklabels(), rotation=45)

#%% Calculate deviance by profile
absolute_diff_profile = validation_results_country1.groupby(level=0).mean() - validation_results_country2.groupby(level=0).mean()
relative_diff_profile = absolute_diff_profile / validation_results_country2.groupby(level=0).mean()

fig, ax = plt.subplots(figsize=(4,4))
sns.heatmap(relative_diff_profile, ax=ax)

#%% Calculate deviance by activity
absolute_diff_activity = validation_results_country1.groupby(level=1).mean() - validation_results_country2.groupby(level=1).mean()
relative_diff_activity = absolute_diff_activity / validation_results_country2.groupby(level=1).mean()

fig, ax = plt.subplots(figsize=(4,4))
sns.heatmap(relative_diff_activity, ax=ax)

#%% Plot relative difference by profile and activity for one metric
metrics = ["mae", "bias", "pearson_corr"]
fig, axs = plt.subplots(figsize=(8,4*len(metrics)), nrows=len(metrics), ncols=1)
axs_flat = axs.flatten()
for i, metric in enumerate(metrics):
    df = relative_diff[metric].reset_index(level=1).pivot(columns="level_1", values=metric)
    sns.heatmap(df, ax=axs_flat[i], cbar_kws={"aspect": 6}, cmap="RdYlGn_r", center=0.0, vmin=relative_diff[metric].quantile(0.05), vmax=relative_diff[metric].quantile(0.95))
        
    axs[i].set_title(f"relative deviance in {metric}")
    axs[i].set_xlabel("")
    if i != len(metrics) - 1:
        axs[i].set_xticklabels(["" for x in axs[0].get_xticklabels()])
fig.tight_layout()