# Speaking Script — Sharath Kashetty (~3 min)

---

*(Point to Col 2 — "Key Algorithms")*

Pradeep's pipeline gives us a graph full of population-level signals. But clinicians don't treat populations — they treat individual patients. A 72-year-old on six drugs has a very different risk profile than a 30-year-old on one. My job was to bridge that gap: turn the graph into a predictive model, and prove the whole system is correct.

---

*(Point to Col 1 — "Data Sources")*

I owned two stages. The first is drug normalization. FAERS reports are messy — "Lipitor", "ATORVASTATIN CALCIUM", and "atorvastatin" are the same drug, but the raw data treats them as three different things. I used the NLM RxNorm API to map every drug string to a standard ingredient name. For anything the API couldn't resolve, I added fuzzy matching as a fallback. That brought unmapped drugs down from about 40% to under 5%.

The engineering challenge here was that concurrent API lookups were deadlocking inside the async event loop. I restructured the lookup as a flattened coroutine pool to fix it.

---

*(Point to Col 2 — "Key Algorithms", then "What Is New")*

The second stage is the ML risk model. I trained three XGBoost classifiers — one each for serious outcome, hospitalization, and death — on eight patient features including age, sex, number of drugs, and a graph-derived PRR signal. I used Optuna to automatically tune the hyperparameters across 50 trials, which was essential because FAERS has severe class imbalance. I also added SHAP explanations so every prediction comes with a ranked list of which features drove the score.

The third stage is validation. I built a ground-truth set of seven known FDA drug–event alert pairs and computed precision, recall, F1, and AUC against them.

---

*(Point to Col 3 — "Top Detected Safety Signals (PRR)", then "Method Comparison")*

The results: all seven FDA alert pairs are detected at 5,000 or more records. AUC for serious outcome is 0.82 at just 50 records, stabilizing at 0.75 to 0.80 at scale. SHAP consistently puts "number of suspect drugs" as the top predictor — polypharmacy is the dominant risk factor, which matches clinical literature.

PRR and ML complement each other. PRR gives you useful signals even at 50 records. The ML model needs more data but gives you individual patient risk with an explanation.

---

*(Point to Col 3 — "Method Comparison")*

The SHAP output doesn't just say "this patient is high risk." It says "this patient is high risk because they are on four suspect drugs and over 65." That is actionable. That is what closes the gap between a population signal and a clinical decision.
