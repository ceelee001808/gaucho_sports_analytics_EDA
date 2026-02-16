import re
import unicodedata
from difflib import SequenceMatcher

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# 1) Load data
bw_path = "/Users/clee/Desktop/Gaucho_sports_data/big_west_transfers.csv"
d2_path = "/Users/clee/Desktop/Gaucho_sports_data/clean_baseball_d2.csv"

bw = pd.read_csv(bw_path)
d2 = pd.read_csv(d2_path)


# 2) Filter Big West transfers to only D2/D3
bw_d23 = bw[bw["Transfer.Level"].isin(["DII", "DIII"])].copy()


# 3) Name cleaning helpers for joining

_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}

def clean_name(s: str) -> str:
    """Normalize a name to improve matching across datasets."""
    if pd.isna(s):
        return ""
    s = str(s)
    s = unicodedata.normalize("NFKD", s)
    s = s.replace(".", " ").replace(",", " ").replace("’", "'").replace("`", "'")
    s = re.sub(r"[^A-Za-z\s'-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip().lower()

    # Split on spaces/hyphens/apostrophes to remove suffixes robustly
    parts = [p for p in re.split(r"[ \-']", s) if p]
    if parts and parts[-1] in _SUFFIXES:
        parts = parts[:-1]
    return " ".join(parts)

def first_last(name_clean: str) -> tuple[str, str]:
    parts = name_clean.split()
    if len(parts) == 0:
        return ("", "")
    if len(parts) == 1:
        return (parts[0], "")
    return (parts[0], parts[-1])

bw_d23["name_clean"] = bw_d23["Player.Name"].map(clean_name)
d2["name_clean"] = d2["player_name"].map(clean_name)

bw_d23[["first", "last"]] = bw_d23["name_clean"].apply(lambda s: pd.Series(first_last(s)))
d2[["first", "last"]] = d2["name_clean"].apply(lambda s: pd.Series(first_last(s)))

bw_d23["first_init"] = bw_d23["first"].str[:1]
d2["first_init"] = d2["first"].str[:1]

# Drop exact duplicates in the transfer list
bw_unique = bw_d23.drop_duplicates(
    subset=["Player.Name", "Team", "Year.s.", "Transfer.Level", "name_clean", "last", "first_init"]
).copy()


# 4) Fuzzy-ish match: (last name + first initial) group, then pick best similarity
d2_group = d2.groupby(["last", "first_init"])

def best_match(row, min_score: float = 0.86) -> str | None:
    key = (row["last"], row["first_init"])
    if key not in d2_group.groups:
        return None

    idx = d2_group.groups[key]
    subset = d2.loc[idx, ["name_clean"]].drop_duplicates()
    target = row["name_clean"]

    # similarity score over cleaned full name
    scores = subset["name_clean"].apply(lambda x: SequenceMatcher(None, target, x).ratio())
    best_idx = scores.idxmax()
    best_score = float(scores.loc[best_idx])

    if best_score < min_score:
        return None
    return str(subset.loc[best_idx, "name_clean"])

bw_unique["best_d2_name_clean"] = bw_unique.apply(best_match, axis=1)
bw_unique["has_d2_stats"] = bw_unique["best_d2_name_clean"].notna()


# 5) Pull each matched player's LAST D2 season (max year) from d2 dataset
d2_sorted = d2.sort_values(["name_clean", "year"])
last_season = d2_sorted.groupby("name_clean", as_index=False).tail(1)

bw_matches = bw_unique[bw_unique["has_d2_stats"]].copy()
bw_matches = bw_matches.merge(
    last_season,
    left_on="best_d2_name_clean",
    right_on="name_clean",
    how="left",
    suffixes=("_bw", "_d2"),
)


# 6) Basic counts / summaries
overall_counts = bw_unique["Transfer.Level"].value_counts()
team_counts = (
    bw_unique.groupby(["Team", "Transfer.Level"])
    .size()
    .reset_index(name="n")
    .sort_values(["n", "Team"], ascending=[False, True])
)

match_summary = (
    bw_unique.groupby(["Transfer.Level", "has_d2_stats"])
    .size()
    .reset_index(name="n")
    .sort_values(["Transfer.Level", "has_d2_stats"])
)

print("\n--- Overall D2/D3 transfer counts ---")
print(overall_counts)

print("\n--- Destination team counts (D2/D3) ---")
print(team_counts.to_string(index=False))

print("\n--- Match rate to D2 stats file ---")
print(match_summary.to_string(index=False))

# Summary stats for matched players (if present)
metrics = [
    "plate_appearances",
    "batting_average",
    "on_base_pct",
    "slugging_pct",
    "ops",
    "home_runs",
    "stolen_bases",
    "walks",
    "strikeouts",
    "wins_above_repl",
    "sos_adj_war",
]

if len(bw_matches) > 0:
    summary = bw_matches[metrics].describe().T[["count", "mean", "std", "min", "25%", "50%", "75%", "max"]]
    print("\n--- Summary: last D2 season stats for matched players ---")
    print(summary.to_string())



#Counts by destination team (bar chart)
plt.figure()
team_total = bw_unique.groupby("Team").size().sort_values(ascending=False)
plt.bar(team_total.index, team_total.values)
plt.xticks(rotation=60, ha="right")
plt.ylabel("Number of transfers (from D2/D3)")
plt.title("Big West incoming transfers from D2/D3 by destination team")
plt.tight_layout()
plt.show()


#Scatter: PA vs OPS for matched players (label points)
if len(bw_matches) > 0:
    plt.figure()
    plt.scatter(bw_matches["plate_appearances"], bw_matches["ops"])
    for _, r in bw_matches.iterrows():
        plt.text(r["plate_appearances"], r["ops"], r["Player.Name"], fontsize=8)
    plt.xlabel("Plate Appearances (last D2 season)")
    plt.ylabel("OPS (last D2 season)")
    plt.title("Matched Big West D2 transfers: PA vs OPS")
    plt.tight_layout()
    plt.show()


#Save filtered extract for you to use later
extract_path = "/mnt/data/big_west_d2_d3_transfers_filtered.csv"
bw_unique[
    ["Player.Name", "Team", "Year.s.", "Transfer.Level", "has_d2_stats", "best_d2_name_clean"]
].to_csv(extract_path, index=False)

print(f"\nSaved filtered extract to: {extract_path}")
