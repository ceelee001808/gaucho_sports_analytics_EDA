# Big West D2/D3 Transfers — Matching + Summary Stats

This script analyzes incoming Big West baseball transfers from Division II (DII) and Division III (DIII) programs. It filters transfers to only D2/D3, then attempts to match D2 transfers to a D2 stats dataset using a lightweight fuzzy name-matching approach. Finally, it prints summary tables, generates plots, and exports a filtered CSV extract.

---

## What this script does

1. Loads two datasets:
   - `big_west_transfers.csv` (transfer list)
   - `clean_baseball_d2.csv` (D2 player season stats)

2. Filters transfers to only DII and DIII (`Transfer.Level` in `"DII"`, `"DIII"`)

3. Cleans player names to improve matching:
   - Unicode normalization (removes accents)
   - Removes punctuation/special characters
   - Lowercases + collapses whitespace
   - Removes suffixes like Jr, Sr, II, III, etc.
   - Creates `name_clean`, `first`, `last`, `first_init`

4. Matches transfers to D2 stats (for D2 transfers):
   - Groups D2 stats by (last name, first initial)
   - Uses `SequenceMatcher` similarity on `name_clean`
   - Keeps match if similarity score ≥ 0.86
   - Creates `best_d2_name_clean` and `has_d2_stats`

5. Pulls each matched player’s most recent D2 season:
   - Sorts D2 stats by year
   - Takes the last row per player (max year)

6. Prints summary outputs:
   - Overall DII vs DIII transfer counts
   - Destination team counts (by DII/DIII)
   - Match rate to the D2 stats file
   - Descriptive stats for matched players (OPS, PA, WAR, etc.)

7. Generates two plots:
   - Bar chart: transfers by destination team
   - Scatter: Plate Appearances vs OPS for matched D2 players (with labels)

8. Exports a filtered CSV extract with key columns for later use.

## Requirements

Python 3.10+ recommended (works with 3.12).

Install dependencies:

```bash
pip install pandas numpy matplotlib
