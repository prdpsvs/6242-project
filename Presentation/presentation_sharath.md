# Presentation Notes — Sharath Kashetty
**Role: Drug Normalization, ML Models & Validation**
**Time: ~3 minutes**

---

## 🗺️ Poster Section Map — Know Before You Present

| Column | Sections (top → bottom) |
|---|---|
| **Left (Col 1)** | The Problem · Why It Matters · Data Sources · Data Characteristics |
| **Middle (Col 2)** | Our Approach · Key Algorithms · What Is New |
| **Right (Col 3)** | Drug–Adverse Event Network · Pipeline Run Results · Top Detected Safety Signals (PRR) · Method Comparison |
| **Footer** | Conclusion · Future Work · Tech Stack & Links |

> **📌 POSTER callouts below** tell you exactly which section to point at and when.

---

## Opening — The Two Gaps (30 sec)

> "Pradeep's pipeline gives us a graph full of population-level signals. But clinicians don't treat populations — they treat individual patients. A 72-year-old on six drugs has a very different risk profile than a 30-year-old on one. My job was to bridge that gap: turn the graph into a predictive model, and prove that both the signals and the predictions are correct."

> 📌 **POSTER → Col 2: "Key Algorithms"** (orange header) — point to the XGBoost + SHAP row and the PRR formula row. These are the two tools you built.

---

## What I Built (75 sec)

**Drug normalization (Stage 2):**
- FAERS drug name strings are inconsistent — "Lipitor", "ATORVASTATIN CALCIUM", "atorvastatin" are the same drug.

> 📌 **POSTER → Col 1: "Data Sources"** (teal header) — point to the openFDA + RxNorm API logos/bullets. Explain RxNorm is the standard drug vocabulary.
- Used the **NLM RxNorm API** to map every drug string to a canonical RxNorm ingredient.
- For unknowns the API cannot resolve, added `rapidfuzz` fuzzy matching as a fallback with a cached result store. This reduced unmapped drugs from ~40% to under 5%.
- Key engineering challenge: **concurrent RxNorm lookups deadlock** when asyncio semaphores are nested inside an already-running event loop. Solved by restructuring the lookup as a flattened coroutine pool.

**ML risk model (Stage 5):**
- Three XGBoost classifiers: P(serious outcome), P(hospitalization), P(death).
- Feature set: age, sex, number of suspect drugs, number of reactions, report year, reporter type, country, and a PRR-derived graph signal feature.
- **Optuna hyperparameter optimization** (50 trials) automatically tunes max_depth, learning rate, and class_weight to handle FAERS's severe class imbalance.
- Added **SHAP explanations** per prediction so each output comes with a ranked list of which features drove that patient's score.

> 📌 **POSTER → Col 2: "Key Algorithms"** — point to the XGBoost + Optuna + SHAP row.
> Then **Col 2: "What Is New"** (purple header) — point to the bullet about *"individual patient risk with SHAP explanation"*.

**Validation (Stage 6):**
- Built a ground-truth set of 7 known FDA drug–event alert pairs.
- Computed precision, recall, F1, and AUC-ROC against that set.

---

## How It Fits the Whole Solution (30 sec)

> "Normalization is what makes the graph meaningful — without it, warfarin and COUMADIN appear as separate nodes. Validation is what gives the whole system credibility — we're not just running an algorithm, we're showing it recovers signals the FDA already confirmed."

> 📌 **POSTER → Col 3: "Top Detected Safety Signals (PRR)"** (orange header) — point to the 7-row table with drug/AE pairs and PRR values.
> Then sweep right to **Col 3: "Method Comparison"** (dark header) — point to the row showing our system vs. OpenVigil vs. VigiAccess.

---

## Key Results (30 sec)

- All **7 ground-truth FDA alert pairs detected** at ≥ 5,000 records (PRR ≥ 2 for all).

> 📌 **POSTER → Col 3: "Top Detected Safety Signals (PRR)"** — point to the checkmarks in the FDA Alert column.

- AUC(serious) = **0.82 at 50 records**, stabilizes at **0.75–0.80 at ≥ 5k records**.
- SHAP consistently ranks **"number of suspect drugs"** as the top predictor — polypharmacy as the dominant risk factor, consistent with clinical literature.
- PRR and ML complement each other: PRR is useful even at 50 records; ML requires ~500+ records per class.

> 📌 **POSTER → Col 3: "Pipeline Run Results"** (green header) — point to the Communities and Runtime columns to show scale.

---

## Closing Line (15 sec)

> "The SHAP output doesn't just say 'this patient is high risk' — it says 'this patient is high risk because they're on four suspect drugs and over 65.' That's actionable. That's what closes the gap between a population signal and a clinical decision."

---

## Anticipated Questions

| Question | Answer |
|---|---|
| Why XGBoost and not logistic regression? | Gradient-boosted trees handle class imbalance and non-linear feature interactions better. AUC is ~10 points higher in our tests. |
| AUC = 0.50 for hospitalization at small N — isn't that random? | Yes — 48 serious, 2 non-serious at 50 records makes the hospitalization classifier degenerate. Disclosed as a known limitation. Meaningful only at ≥ 1k records per class. |
| Why only 7 ground-truth pairs? | These are the FDA-published confirmed alerts for the drugs in our test set. A larger validation set is listed as future work. |
