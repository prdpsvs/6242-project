# Speaking Script — Venkata Satya Pradeep Srikakolapu (~3 min)

---

*(Point to Col 1 — "The Problem")*

A doctor has a patient on six drugs who just had a serious reaction. They need to know — is this a known risk? Today that means downloading gigabytes of files and waiting days. We made it one command. Seconds.

---

*(Point to Col 2 — "Our Approach" — finger on Step 1, walk to Step 6)*

I designed the architecture. Six stages, each handing off to the next.

One: pull live reports straight from the FDA API. Two: standardize drug names — "Lipitor" and "Atorvastatin Calcium" are the same drug. Three: I build a network — drugs on one side, side effects on the other, edges weighted by co-occurrence. Four: a clustering algorithm groups drugs by shared side effect patterns — no labels, pure data. Five: Sharath's model predicts individual patient risk. Six: Sunil's dashboard makes it interactive.

Every stage is connected by typed data contracts. Nothing breaks silently.

---

*(Point to Col 2 — "What Is New", then Col 3 — "Top Detected Safety Signals (PRR)")*

Two hard problems I solved.

The FDA API uses a query syntax that standard URL libraries silently mangle. Every request failed with no error. I built the query strings by hand. I also rate-limited ourselves to five concurrent requests so we never get throttled — even at 50,000 records.

Then I compute PRR — Proportional Reporting Ratio — for every drug–side effect pair. One question: is this pair reported far more than chance would predict? Ratio of 2 or above — it's a signal.

---

*(Point to Col 3 — "Top Detected Safety Signals (PRR)", then "Pipeline Run Results")*

All seven known FDA alert pairs recovered. Warfarin and bleeding. Atorvastatin and muscle damage. Five more. Fifty records runs in 10 seconds. Fifty thousand records — 35 minutes. Linear scaling.

---

*(Click aspirin node on the dashboard — show sidebar AE list, then run patient risk prediction)*

Here's aspirin live. Click the node — GI bleed, hemorrhage, top adverse events ranked by signal strength. Now enter a 65-year-old on aspirin and warfarin. Hit predict. Serious outcome risk — 78%. SHAP tells you why: two suspect drugs, age over 60. That's the whole system in 30 seconds.

---

*(Point to Footer — "Conclusion")*

We started with a problem that takes days. We made it seconds. Live data. No downloads. Individual risk with an explanation. That's what we built. Thank you.
