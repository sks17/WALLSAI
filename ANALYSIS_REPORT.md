# Repository Data & Pipeline Analysis (Current State)

## 1) CSV Inventory & Usage
- Located in `newData/`:
  - `Abadi... .csv`, `Abadi... _cleaned.csv`, `Abadi... _cleaned_cleaned.csv`
  - `mental_health_finaldata_1.csv`, `_cleaned.csv`, `_cleaned_cleaned.csv`
  - `mmc2.csv`, `_cleaned.csv`, `_cleaned_cleaned.csv`
  - `pone.0246894.s005.csv`, `_cleaned.csv`, `_cleaned_cleaned.csv`
  - Debug: `column_inventory_debug.txt`
- Other CSVs:
  - `Static/Data/dataset.csv` (legacy/decision-tree use)
  - `Static/junk.csv` (placeholder)
  - Generated: `unified_training.csv` (root)
- Script usage:
  - `clean_data.py`: processes every `*.csv` in `newData/`, outputs `<name>_cleaned.csv` (and on re-run, `_cleaned_cleaned.csv`).
  - `build_unified_dataset.py`: now loads both `_cleaned.csv` and `_cleaned_cleaned.csv`.
  - `train_models.py`: reads `unified_training.csv`.
  - `Static/Data/dataset.csv` only used by legacy code (`ml/train.py`, `legacy/disorder.py`).

## 2) Script Behaviors
### clean_data.py
- BOM-strips column headers, strips cell whitespace, normalizes yes/no/maybe, age ranges, sleep/time; detects Likert (casts to Int64).
- Flags reverse-coded columns (removes trailing “*”).
- Attempts PHQ9/GAD7 totals on matching text; may not find all.
- Final drop: only rows that are **all NaN** (`dropna(how="all")`); preserves partial rows.
- Re-running produces `_cleaned_cleaned.csv` duplicates.

### build_unified_dataset.py
- Loads `_cleaned` and `_cleaned_cleaned` from `newData/`; adds `source_dataset`.
- Debug: prints columns and writes `newData/column_inventory_debug.txt`.
- Fuzzy mapping for demographics and symptom items:
  - Demographics via fuzzy similarity (threshold ~0.65).
  - PHQ-9: fuzzy phrases (little interest, feeling down, trouble falling, low energy, poor appetite, feeling bad, trouble concentrating, moving slowly, dead/hurting yourself).
  - GAD-7: fuzzy phrases (nervous, can’t control worrying, worrying too much, trouble relaxing, restless, irritable, something awful might happen).
  - Stress: keywords (stress, infection, economic, difficulty, loss, disturbance, adaptive).
  - Sleep: fuzzy phrases (sleep latency, fall asleep, wake up, hours of actual sleep, hours in bed, sleep quality, bathroom, snore, night awakening, dreams, temperature, pain).
- Scoring: if <2 valid columns → all-NaN Series; otherwise per-column numeric coercion then sum/mean.
- Currently does **not** drop rows after concatenation (previous global drop removed).

### train_models.py
- Reads `unified_training.csv`; drops rows where **all three** targets are NaN.
- Robust preprocessing: imputers + scaling/one-hot; TF-IDF “noop” fallback.
- Models: HistGradientBoostingRegressor; skips if <20 rows for a target.

## 3) Column Mismatches (Why NaNs)
From `column_inventory_debug.txt`:
- Abadi datasets: columns are coded (`a3_1` … `a40_11`, plus respondentid, country). No descriptive text; fuzzy mapping cannot find demographics/PHQ/GAD/sleep/stress → all targets and demographics NaN.
- mental_health_finaldata_1: columns include age/gender/occupation, growing_stress, quarantine_frustrations, changes_habits, mental_health_history, weight_change, mood_swings, coping_struggles, social_weakness. Stress mapping requires ≥2 cols; only one stress-like col (“growing_stress”) → stress_score NaN; no PHQ/GAD/sleep items → targets NaN.
- mmc2: long question strings for demographics, PHQ-9 (9), GAD-7 (7), sleep items. Fuzzy phrases should match, but must be verified; stress items likely absent.
- pone.0246894.s005: stress-related columns exist (fear_of_infection, difficulty_in_outside_activities, economic_loss, disturbance_in_eating_and_sleeping, adaptive_stress, perception_of_stress) → stress_score should compute; no PHQ/GAD/sleep/demographics.
- Duplicates: `_cleaned` and `_cleaned_cleaned` both read, duplicating rows.
- Train_models drops rows with all targets NaN; if PHQ/GAD mapping fails for mmc2 and stress mapping only works for pone, most rows are dropped, leading to “rows=0, features=0” warnings.

## 4) Data Loss / Drops
- clean_data.py now only drops fully-empty rows, so main loss is not from cleaning.
- build_unified_dataset.py no longer drops after concat; but train_models drops rows with all targets NaN, effectively discarding datasets that fail target mapping (Abadi; mental_health_finaldata_1; potentially mmc2 if fuzzy fails).

## 5) Root Causes
- Abadi dataset uses short codes with no text → fuzzy mapping can’t map demographics or symptom items → all NaN targets/demographics from this dataset.
- mental_health_finaldata_1 has only one stress column; PHQ/GAD/sleep absent → targets NaN.
- Stress scoring requires ≥2 columns; single stress fields yield NaN.
- PHQ/GAD fuzzy phrases may still miss mmc2 columns if similarity < threshold; need verification but risk remains.
- Reading both `_cleaned` and `_cleaned_cleaned` duplicates datasets (not fatal but inflates counts).
- train_models drops rows with all targets NaN; if only pone contributes stress and mmc2 fails PHQ/GAD detection, most rows vanish, causing skipped models.

## 6) Scripts Touching CSVs
- `clean_data.py`: reads all CSVs in `newData/`, writes cleaned variants.
- `build_unified_dataset.py`: reads cleaned variants; writes `unified_training.csv`; outputs `column_inventory_debug.txt`.
- `train_models.py`: reads unified_training.csv.
- Legacy: `ml/train.py`, `legacy/disorder.py` read `Static/Data/dataset.csv`.
- No other data-processing scripts found.

## 7) Transformations Summary
- Column headers: cleaner strips BOM/whitespace only; builder standardizes to lowercase + underscores + dedupe.
- Values: yes/no/maybe normalization; age normalization; sleep/time normalization; Likert detection may cast to Int64; empty strings → NaN.
- PHQ/GAD totals added in cleaner only if patterns found; otherwise absent.

## 8) Why Demographics & Scores Are NaN in Unified Output
- Abadi: unmappable short codes.
- mental_health_finaldata_1: only one stress column, no PHQ/GAD/sleep.
- mmc2: mapping depends on fuzzy match success; if phrases don’t meet threshold, PHQ/GAD fail.
- pone: only stress (no demo/PHQ/GAD/sleep).
- Result: many rows have all targets NaN → dropped in train_models → models skipped.

## 9) Notes
- Debug file `column_inventory_debug.txt` shows actual columns; mappings must be aligned to these.
- Reminder to run manually:
  - `python build_unified_dataset.py`
  - `python train_models.py`

## 10) Dataset Descriptions and Columns

Below is a concise description of each CSV and its columns, based on the debug inventory and `DATA_DICTIONARY.md`. Column names may appear in multiple cleaned versions (`_cleaned`, `_cleaned_cleaned`) with identical schemas.

### Abadi et al. (2023) COVID-19 (4-country) Survey
- Files: `Abadi ... .csv`, `_cleaned.csv`, `_cleaned_cleaned.csv`
- Columns: `respondentid`, `country`, then coded items `a3_1` … `a40_11` (~120 items). These are Likert-coded socio-psychological, emotional, threat, conspiracy, hygiene, and demographic instruments. No human-readable question text is present in the CSV; requires an external codebook.

### mental_health_finaldata_1
- Files: `mental_health_finaldata_1.csv`, `_cleaned.csv`, `_cleaned_cleaned.csv`
- Columns: `age`, `gender`, `occupation`, `days_indoors`, `growing_stress`, `quarantine_frustrations`, `changes_habits`, `mental_health_history`, `weight_change`, `mood_swings`, `coping_struggles`, `work_interest`, `social_weakness`, `source_dataset`.
- Short, categorical survey on stress, lifestyle change, mood, coping, social factors.

### mmc2
- Files: `mmc2.csv`, `_cleaned.csv`, `_cleaned_cleaned.csv`
- Columns include:
  - Demographics: consent, age range, sex, BMI, marital status, education, occupation, economic status, residence, living status, smoking.
  - Loneliness (8 items, past 30 days).
  - PHQ-9 depression (9 items, past two weeks).
  - GAD-7 anxiety (7 items, past two weeks).
  - Sleep timing/quality/frequency (19+ items: bed/wake times, hours slept/in bed, awakenings, bathroom, breathing, snore, temperature, dreams, pain, sleep meds, sleep quality, etc.).
  - `phq9_total` (from cleaner when detected), `source_dataset`.

### pone.0246894.s005
- Files: `pone.0246894.s005.csv`, `_cleaned.csv`, `_cleaned_cleaned.csv`
- Columns: `id`, `fear_of_infection`, `difficulty_in_outside_activities`, `economic_loss`, `disturbance_in_eating_and_sleeping`, `adaptive_stress`, `perception_of_stress`, `source_dataset`.
- Compact COVID-related stress scale.

### Legacy dataset (not in unified pipeline)
- `Static/Data/dataset.csv`: legacy symptom/disorder dataset used only by legacy decision-tree code (`ml/train.py`, `legacy/disorder.py`).

