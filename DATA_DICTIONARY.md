# DATA DICTIONARY

## 1. Overview of All Datasets

- **Abadi et al. (2023) A Dataset of Social-Psychological and Emotional Reactions during the COVID-19 Pandemic across Four European Countries.csv**  
  Cross-sectional online survey (April 2020) across Germany, Netherlands, Spain, UK (~2,031 rows; ~120 columns). Columns are coded items (e.g., `A3.1`, `A5.3*`, `A9.3*`) representing socio-psychological, emotional, socio-political, conspiracy, threat-perception, hygiene compliance, and demographic measures. Numeric Likert responses; asterisks denote reverse-coded items. Requires codebook for precise item wording.

- **mental_health_finaldata_1.csv**  
  Small mental-health survey (~800 rows; 13 columns). Mix of categorical ranges and Yes/No/Maybe for stress, habits, prior history, weight change, mood/coping, social/occupational impacts.

- **mmc2.csv**  
  Mental health, loneliness, depression (PHQ-9), anxiety (GAD-7), and sleep quality dataset (~1,500 rows; 57 columns). Includes demographics (consent, age range, sex, BMI class, marital/education/occupation/economic/residence/living/smoking), followed by loneliness items (past 30 days), PHQ-9 depression items (past 2 weeks), GAD-7 anxiety items (past 2 weeks), and sleep timing/quality/frequency items.

- **pone.0246894.s005.csv**  
  Short scale (~1,500 rows; 7 columns) capturing stress related to COVID-19: fear of infection, difficulty in outside activities, economic loss, disturbance in eating/sleeping, adaptive stress, perception of stress.

Similarities/differences: All are survey-based. Two medium/large mental health surveys (`mmc2`, `Abadi...`) with many Likert items; `mental_health_finaldata_1` is concise with broad categories; `pone.0246894.s005` is a compact stress scale. `Abadi...` is multinational COVID early-pandemic; others appear more general or single-population. Likely independent datasets (no shared IDs or schema).

## 2. Column Explanations (Dataset by Dataset)

### Abadi et al. (2023) ...COVID-19 Pandemic... (requires codebook)
The provided `dataset1explanation.txt` does not include column-level mappings for the coded headers (`A3.1`, `A5.3*`, etc.). Accurate definitions need the official codebook. Known patterns:
- `RespondentID`: participant identifier.
- `Country`: coded country (1=Germany, 2=Netherlands, 3=Spain, 4=UK).
- `A*` blocks: Likert items covering appraisals (anger, anxiety), perceived threats, threat estimation, conspiracy mentality, populist attitudes, moral reasoning, hygiene compliance, prosocial behavior, news processing, civil/privacy attitudes, demographics, infection status, feeling status, etc. Asterisks (*) indicate reverse-coded items in the original instrument.

**Meaning unclear — additional metadata required for all `A#.#` columns.** Obtain the official instrument/codebook to map each code to its question text and scale direction.

### mental_health_finaldata_1.csv (inferred)
| Column | Description (inferred) |
| --- | --- |
| Age | Age range (e.g., 16-20, 20-25, 25-30, 30-Above). |
| Gender | Male/Female. |
| Occupation | Corporate, Business, Student, Housewife, Others. |
| Days_Indoors | Duration mostly indoors (Go out every day; 1-14; 15-30; 31-60; More than 2 months). |
| Growing_Stress | Self-reported growing stress (Yes/No/Maybe). |
| Quarantine_Frustrations | Frustration during quarantine (Yes/No/Maybe). |
| Changes_Habits | Changes in habits (Yes/No/Maybe). |
| Mental_Health_History | Prior mental health history (Yes/No/Maybe). |
| Weight_Change | Weight change during period (Yes/No/Maybe). |
| Mood_Swings | Mood swings severity (Low/Medium/High). |
| Coping_Struggles | Struggles coping (Yes/No/Maybe). |
| Work_Interest | Loss of interest in work/study (Yes/No/Maybe). |
| Social_Weakness | Social weakness/withdrawal (Yes/No/Maybe). |

### mmc2.csv (partially known from headers)
| Column | Description |
| --- | --- |
| 1. Express your consent... | Consent to participate. |
| 2. Age range in years | Age bracket. |
| 3. Sex | Sex. |
| 4. Weight and height ratio/BMI score | BMI category. |
| 5. Marital status | Marital status. |
| 6. Education level | Education level. |
| 7. Occupation | Occupation. |
| 8. Economic status | Economic status. |
| 9. Residence area | Urban/Rural. |
| 10. Living status | With/without family. |
| 11. Smoking habit | Smoker/non-smoker frequency. |
| Loneliness items (past 30 days) | Items 1–8: companionship, isolation, feeling left out, etc. (Likert). |
| PHQ-9 items (past 2 weeks) | Items 1–9: interest, mood, sleep, energy, appetite, self-worth, concentration, psychomotor, self-harm thoughts. |
| GAD-7 items (past 2 weeks) | Items 1–7: nervousness, worry, control worry, relaxation, restlessness, irritability, fear of awful events. |
| Sleep timing/quality items | Bedtime, sleep latency, wake time, hours slept, hours in bed, frequency of sleep problems (cannot sleep, awakenings, bathroom, breathing, cough/snore, temperature issues, dreams, pain, other reasons), sleep meds, skipped sleep, enthusiasm, overall sleep quality. |

(Headers contain full question text; scales encoded as categorical phrases or numeric brackets.)

### pone.0246894.s005.csv (inferred)
| Column | Description (inferred) |
| --- | --- |
| ID | Participant identifier. |
| fear of infection | Perceived fear of infection (numeric scale). |
| difficulty in outside activities | Difficulty performing outside activities (numeric). |
| economic loss | Perceived economic loss (numeric). |
| disturbance in eating and sleeping | Disturbance in eating/sleeping (numeric). |
| adaptive stress | Adaptive stress level (numeric). |
| perception of stress | Overall perceived stress (numeric). |

## 3. Recommended New File Names

| Current File | Suggested Name | Rationale |
| --- | --- | --- |
| Abadi et al. (2023) A Dataset of Social-Psychological and Emotional Reactions during the COVID-19 Pandemic across Four European Countries.csv | `COVID19_SocioPsych_4Countries_Apr2020_Raw.csv` | Captures topic, scope, countries, date; indicates raw survey. |
| mental_health_finaldata_1.csv | `MentalHealth_LifestyleStress_ShortSurvey_Raw.csv` | Short mental-health/stress/lifestyle survey; raw form. |
| mmc2.csv | `MentalHealth_Loneliness_Depression_Anxiety_Sleep_Raw.csv` | Contains loneliness, PHQ-9, GAD-7, sleep items; raw survey. |
| pone.0246894.s005.csv | `COVID19_StressFactors_ShortScale_Raw.csv` | Compact stress-factor scale related to COVID-19; raw survey. |

## 4. Suggestions for Improved Dataset Organization

- **Folder structure**
  - `data/raw/` — original CSVs as received.
  - `data/interim/` — cleaned/typed versions (consistent encodings, trimmed headers).
  - `data/processed/` — analysis-ready (coded factors, labeled columns, derived scores).
  - `docs/` — codebooks, PDFs, data dictionaries.

- **Naming conventions**
  - `topic_population_period_status.csv` (e.g., `COVID19_StressFactors_EU_Apr2020_raw.csv`).
  - Use lowercase with underscores; avoid spaces and special characters.

- **Preprocessing recommendations**
  - Standardize encodings (UTF-8), strip BOMs.
  - Normalize categorical values (e.g., Yes/No/Maybe; age ranges).
  - Add codebooks: map numeric Likert to labels; document reverse-coded items.
  - Handle missing values explicitly; record imputation strategy.
  - For `Abadi...`, acquire official codebook to decode `A#.#` columns; mark reverse-coded items before scoring.
  - For PHQ-9/GAD-7 in `mmc2`, compute validated total scores after ensuring correct scaling.
  - For sleep items, standardize time formats (HH:MM) and durations (minutes/hours).
  - Version datasets; retain row counts and checksums after each transformation.

