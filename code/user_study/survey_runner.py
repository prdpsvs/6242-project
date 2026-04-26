"""Simple in-memory user study survey runner.
Owner: Sunil Mannuru
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict

QUESTIONS = [
    "How easy was it to find information about a specific drug? (1=Very hard, 5=Very easy)",
    "How clearly did the network visualize drug–adverse-event relationships? (1=Very unclear, 5=Very clear)",
    "How useful was the outcome prediction feature? (1=Not useful, 5=Very useful)",
    "How confident are you in the analysis results? (1=Not confident, 5=Very confident)",
    "Would you use this tool in a professional context? (1=Definitely not, 5=Definitely yes)",
    "Any other comments (freeform):",
]


@dataclass
class Response:
    participant_id: str
    timestamp: float
    answers: list


def run_survey(participant_id: str) -> Response:
    """Interactive CLI survey — answers collected in-memory."""
    print(f"\n=== User Study — Participant {participant_id} ===\n")
    answers = []
    for q in QUESTIONS:
        ans = input(f"  {q}\n  > ").strip()
        answers.append(ans)
    return Response(participant_id=participant_id, timestamp=time.time(), answers=answers)


def summarize(responses: list[Response]) -> dict:
    """Compute mean scores for Likert items (Q1-Q5)."""
    if not responses:
        return {}
    n = len(responses)
    scores: list[list[float]] = [[] for _ in range(5)]
    for resp in responses:
        for i in range(5):
            try:
                scores[i].append(float(resp.answers[i]))
            except (ValueError, IndexError):
                pass
    means = [round(sum(s) / len(s), 2) if s else None for s in scores]
    comments = [r.answers[5] if len(r.answers) > 5 else "" for r in responses]
    return {
        "n_participants": n,
        "mean_scores": {QUESTIONS[i][:50]: means[i] for i in range(5)},
        "comments": comments,
    }
