from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, List


SIMILARITY_SECTIONS = ("stp", "branding", "channels", "content_strategy", "launch_plan")


def _flatten(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, (int, float, bool)):
        return str(value).lower()
    if isinstance(value, list):
        return " ".join(_flatten(item) for item in value if item is not None)
    if isinstance(value, dict):
        parts: List[str] = []
        for key in sorted(value):
            parts.append(key.replace("_", " ").lower())
            parts.append(_flatten(value[key]))
        return " ".join(part for part in parts if part)
    return str(value).lower()


def strategy_text_signature(strategy: Dict[str, Any], sections: Iterable[str] = SIMILARITY_SECTIONS) -> str:
    return " ".join(_flatten((strategy or {}).get(section)) for section in sections).strip()


def compare_with_history(strategy: Dict[str, Any], previous_rows: List[Dict[str, Any]], threshold: float = 0.82) -> Dict[str, Any]:
    current_signature = strategy_text_signature(strategy)
    best_score = 0.0
    best_match_id = None

    for row in previous_rows:
        other_strategy = row.get("strategy") if isinstance(row.get("strategy"), dict) else row
        other_signature = strategy_text_signature(other_strategy)
        if not current_signature or not other_signature:
            continue
        score = SequenceMatcher(None, current_signature, other_signature).ratio()
        if score > best_score:
            best_score = score
            best_match_id = row.get("id")

    return {
        "score": round(best_score, 4),
        "threshold": threshold,
        "too_similar": best_score >= threshold,
        "matched_strategy_id": best_match_id,
        "compared_count": len(previous_rows),
    }
