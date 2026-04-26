# Presentation Notes — Venkata Satya Pradeep Srikakolapu
**Role: Solution Architecture, Data Ingestion & Graph Analytics**
**Time: ~3 minutes**

---

## 🗺️ Poster Section Map — Know Before You Present

| Column | Sections (top → bottom) |
|---|---|
| **Left (Col 1)** | The Problem · Why It Matters · Data Sources · Data Characteristics |
| **Middle (Col 2)** | Our Approach · Key Algorithms · What Is New |
| **Right (Col 3)** | Drug–Adverse Event Network · Pipeline Run Results · Top Detected Safety Signals (PRR) · Method Comparison |
| **Footer** | Conclusion · Future Work · Tech Stack & Links |

> **📌 POSTER callouts below** tell you exactly which section to point at and when. Practice the hand gesture before presenting.

---

## Opening — The Problem in Plain English (30 sec)

> "Imagine you are a doctor. Your patient is on six different medications and just had a serious reaction. You want to know — is this a known risk? Has the FDA seen this before? Right now, answering that question means downloading gigabytes of files, running scripts, and waiting days. We built a system where you just run one command and get the answer in seconds."

> 📌 **POSTER → Col 1: "The Problem"** (blue header, top-left card) — point to the first bullet: *"over 2 million adverse event reports per year."*
> Then sweep hand down to **Col 1: "Why It Matters"** (orange header) — point to the Vioxx recall stat.

---

## How the Whole System Works — The Architecture (60 sec)

> "Before I talk about my piece, let me show you how the whole thing fits together — because I designed the architecture."

> 📌 **POSTER → Col 2: "Our Approach"** (blue header, top of middle column) — place your finger on Step 1 and walk it down through Step 6 as you speak each stage below.

**Six stages, each handing off to the next:**

1. **Fetch** — We ask the FDA's live API for adverse event reports. No files, no downloads — straight from the source.
2. **Clean** — Drug name strings like "Lipitor" and "ATORVASTATIN CALCIUM" are the same drug. Sharath's module maps them all to a single standard name.
3. **Build the graph** — I turn those cleaned records into a network: drugs on one side, side effects on the other. Every connection is weighted by how often they appear together.
4. **Find communities** — The graph naturally clusters drugs that share similar side effect profiles — statins together, blood thinners together — with no manual labeling.
5. **Predict risk** — Sharath's ML model takes a patient's details and estimates their personal risk of a serious outcome.
6. **Show it** — Sunil's dashboard makes all of this explorable in a browser.

> "What holds this together is a set of typed data contracts between every stage. When I hand off the graph, Sharath's code always knows exactly what shape the data is in. No guessing, no crashes."

> 📌 **POSTER → Col 2: "What Is New"** (purple header) — point to the bullet about *"no-storage, fully live API pipeline"* to reinforce the architecture novelty.

---

## The Hard Part — What I Solved (45 sec)

**Challenge 1 — Getting the data reliably:**
- The FDA's API uses a special query format that most standard libraries silently break. URLs were being mangled and requests were failing with no error message. I had to build the query string by hand.
- The API also has a rate limit. I added a traffic controller so we never send more than 5 requests at once — at 50,000 records that keeps us running smoothly for ~35 minutes instead of getting blocked.

**Challenge 2 — Turning data into a signal:**
- Once we have the graph, I compute a score called PRR — Proportional Reporting Ratio — for every drug/side-effect pair. Think of it as: "Is this pair reported way more often than you'd expect by chance?" If PRR ≥ 2, it's a signal worth flagging.

> 📌 **POSTER → Col 2: "Key Algorithms"** (orange header) — point to the PRR formula row.
> Then move right to **Col 3: "Top Detected Safety Signals (PRR)"** (orange header) — show the table of warfarin, atorvastatin, etc.

---

## Key Results (30 sec)

- **All 7 known FDA drug–event alerts are recovered** when given enough data — warfarin causing bleeding, atorvastatin causing muscle damage, and five others.

> 📌 **POSTER → Col 3: "Top Detected Safety Signals (PRR)"** — point to the 7-row PRR table.

- At 50 records the system runs in **10 seconds**. At 50,000 records, **35 minutes**. It scales linearly.

> 📌 **POSTER → Col 3: "Pipeline Run Results"** (green header) — point to the scalability table (20 / 50 / 50k rows).

- Drug communities emerge automatically — anticoagulants cluster together, statins cluster together — purely from the data, no labels given.

> 📌 **POSTER → Col 3: "Drug–Adverse Event Network"** (green header) — point to the network SVG and the colored clusters.

---

## Closing Line (15 sec)

> "The whole system runs in memory. You type one command, it fetches live data, builds the graph, trains the model, and serves the dashboard. Nothing written to disk. Any reviewer anywhere in the world can reproduce our exact results right now."

---
