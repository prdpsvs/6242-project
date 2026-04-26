# Speaking Script — Sunil Mannuru (~3 min)

---

*(Point to Col 3 — "Drug–Adverse Event Network")*

Pradeep produces a graph. Sharath produces risk scores. None of that matters if no one can use it. My job was to make everything explorable in a browser, with no setup, in under 90 seconds.

---

*(Point to Col 2 — "Key Algorithms")*

I built two things. First, the server. After the pipeline runs, a FastAPI server holds all the data in memory and exposes six endpoints — graph data, community labels, drug neighborhoods, predictions, statistics, and validation results. No database, no disk reads. Everything lives in process memory.

The engineering challenge here was that Python's JSON encoder rejects not-a-number float values, and our ML models sometimes produce them for features that never appear in the data. I wrote sanitizer functions that replace NaN and infinity with null or zero before serialization. Without that fix, the server crashes the first time you query it on a real dataset.

---

*(Point to Col 3 — "Drug–Adverse Event Network", point to the color legend)*

Second, the dashboard. The main view is a force-directed network built with D3.js. Drug nodes are blue, adverse event nodes are orange. Edge color encodes signal strength — red edges are high-confidence signals with PRR of 5 or more, orange edges are signals above 2, gray edges are below threshold. Edge width also scales with the PRR value, so you can read signal strength at a glance.

---

*(Point to Col 3 — "Top Detected Safety Signals (PRR)")*

Click any drug node and the non-neighbors dim out. A sidebar appears showing the top five adverse events for that drug, ranked by PRR. The table you see on the poster — that is exactly what the Top Safety Signals panel displays in the live dashboard.

The prediction panel takes age, sex, and a drug list. It returns probability bars for serious outcome, hospitalization, and death, with SHAP feature contributions listed beneath so you know why the score is what it is.

---

*(Point to Col 3 — "Pipeline Run Results", then Footer — "Future Work")*

In our usability test, three users with no prior training completed the full workflow — find a drug, view its adverse events, run a prediction — within 90 seconds. The dashboard handles up to about 2,000 nodes smoothly. Beyond that, the force simulation slows down. A WebGL renderer is the planned fix, listed in Future Work on the poster.

---

*(Sweep hand across the full poster)*

What we built is the only system that combines live signal detection, community clustering, individual risk prediction, and interactive drill-down in a single pipeline. No downloads. No stale data. One command.
