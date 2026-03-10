"""
Deterministic entity resolver.

Scans every $match stage in a MongoDB aggregation pipeline and validates
field values that could produce confusing or empty results:
  1. $regex / $not{$regex} — checks how many distinct values match
  2. $in / $nin with string values — checks how many of the provided names exist

Returns a needs_clarification signal with candidates when something looks off.
"""

from typing import Any, Dict, List

from app.db.mongo import runAggregation


# Fields whose values are free-text entity names that must be validated for ambiguity / existence
ENTITY_LIKE_FIELDS = {
    "department_name",
    "supplier_name",
    "commodity_title",
    "item_description",
}

# Fields that use $regex legitimately and should never trigger a clarification check
NON_ENTITY_REGEX_FIELDS = {
    "supplier_qualifications",
}


def _humanField(field: str) -> str:
    """Convert a snake_case field name to a readable label."""
    return field.replace("_", " ").title()


def _orderedList(options: List[str]) -> str:
    return "\n".join(f"{i + 1}. {o}" for i, o in enumerate(options))


def _extractRegexFields(matchSpec: Dict[str, Any], negated: bool = False) -> List[tuple]:
    """
    Recursively extract (field, condition, is_negated) triples where condition contains $regex.
    Handles flat matches, $and/$or/$nor, and $not wrappers.
    """
    found = []
    for key, value in matchSpec.items():
        if key in ("$and", "$or", "$nor") and isinstance(value, list):
            for clause in value:
                if isinstance(clause, dict):
                    found.extend(_extractRegexFields(clause, negated))
        elif isinstance(value, dict):
            if "$regex" in value:
                if key in ENTITY_LIKE_FIELDS:
                    found.append((key, value, negated))
            elif "$not" in value and isinstance(value["$not"], dict) and "$regex" in value["$not"]:
                # field: {$not: {$regex: ...}} — negated regex on a field
                if key in ENTITY_LIKE_FIELDS:
                    found.append((key, value["$not"], True))
            else:
                found.extend(_extractRegexFields(value, negated))
    return found


def _extractLiteralFields(matchSpec: Dict[str, Any]) -> List[tuple]:
    """
    Extract (field, operator, [values]) for $in / $nin on ANY field that contains string values.
    Skips numeric / date-only arrays.
    """
    found = []
    for key, value in matchSpec.items():
        if key in ("$and", "$or", "$nor") and isinstance(value, list):
            for clause in value:
                if isinstance(clause, dict):
                    found.extend(_extractLiteralFields(clause))
        elif not key.startswith("$") and key in ENTITY_LIKE_FIELDS and isinstance(value, dict):
            for op in ("$in", "$nin"):
                if op in value:
                    strings = [v for v in value[op] if isinstance(v, str)]
                    if strings:
                        found.append((key, op, strings))
    return found


def _existingValues(field: str, values: List[str]) -> List[str]:
    """Return which of the given exact values actually exist in the collection."""
    try:
        matches = runAggregation([
            {"$match": {field: {"$in": values}}},
            {"$group": {"_id": f"${field}"}},
            {"$limit": 50},
        ])
        return [m["_id"] for m in matches if m.get("_id") is not None]
    except Exception:
        return values  # can't probe → assume fine


def resolveRegexEntities(pipeline: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate entity references in a pipeline before execution.

    Returns:
        {"status": "ok"}
        {"status": "needs_clarification", "clarifyingQuestion": str, "options": list}
    """
    for stage in pipeline:
        matchSpec = stage.get("$match")
        if not isinstance(matchSpec, dict):
            continue

        # ── 1. Regex fields (positive and negated) ───────────────────────────
        for field, condition, is_negated in _extractRegexFields(matchSpec):
            try:
                matches = runAggregation([
                    {"$match": {field: condition}},
                    {"$group": {"_id": f"${field}"}},
                    {"$sort": {"_id": 1}},
                    {"$limit": 20},
                ])
            except Exception:
                continue

            options = [m["_id"] for m in matches if m.get("_id") is not None]
            label = _humanField(field)

            if is_negated:
                if len(options) == 0:
                    return {
                        "status": "needs_clarification",
                        "clarifyingQuestion": (
                            f"I couldn't find any \"{label}\" matching what you want to exclude. "
                            "Could you double-check the name and try again?"
                        ),
                        "options": [],
                    }
                if len(options) > 1:
                    return {
                        "status": "needs_clarification",
                        "clarifyingQuestion": (
                            f"I found {len(options)} possible matches for **{label}** that could be excluded. "
                            f"Which one did you mean?\n\n{_orderedList(options)}"
                        ),
                        "options": options,
                    }
                # Exactly 1 match — fine, continue
            else:
                if len(options) == 0:
                    return {
                        "status": "needs_clarification",
                        "clarifyingQuestion": (
                            f"I couldn't find any \"{label}\" matching your query. "
                            "Please double-check the name or try a different search term."
                        ),
                        "options": [],
                    }
                if len(options) > 1:
                    return {
                        "status": "needs_clarification",
                        "clarifyingQuestion": (
                            f"I found {len(options)} possible matches for **{label}**. "
                            f"Which one did you mean?\n\n{_orderedList(options)}"
                        ),
                        "options": options,
                    }

        # ── 2. $in / $nin with literal strings — any field ───────────────────
        for field, op, values in _extractLiteralFields(matchSpec):
            existing = _existingValues(field, values)
            label = _humanField(field)
            missing = [v for v in values if v not in existing]

            if op == "$in":
                if len(existing) == 0:
                    return {
                        "status": "needs_clarification",
                        "clarifyingQuestion": (
                            f"I couldn't find any of the \"{label}\" values you provided in the dataset. "
                            "Could you check the spelling or try different names?"
                        ),
                        "options": [],
                    }
                if missing:
                    return {
                        "status": "needs_clarification",
                        "clarifyingQuestion": (
                            f"Some of the **{label}** values you provided don't exist in the dataset:\n\n"
                            f"{_orderedList(missing)}\n\n"
                            "Would you like to proceed with only the ones that were found, or did you mean something different?"
                        ),
                        "options": existing,
                    }

            if op == "$nin":
                if len(existing) == 0:
                    return {
                        "status": "needs_clarification",
                        "clarifyingQuestion": (
                            f"I couldn't find any of the \"{label}\" values you want to exclude in the dataset. "
                            "Could you check the spelling or clarify which ones to exclude?"
                        ),
                        "options": [],
                    }
                if missing:
                    return {
                        "status": "needs_clarification",
                        "clarifyingQuestion": (
                            f"Some of the **{label}** values you want to exclude don't exist in the dataset:\n\n"
                            f"{_orderedList(missing)}\n\n"
                            "Did you mean to exclude different ones?"
                        ),
                        "options": existing,
                    }

    return {"status": "ok"}

