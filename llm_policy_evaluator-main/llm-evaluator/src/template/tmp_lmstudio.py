small_context = """
Goal: Decide if the descriptor satisfies the policy. Be deterministic, vendor-agnostic, and concise.

Normalization & safety:
- Compare keys case-insensitively; map '-', '_' and spaces to a single separator.
- Trim strings. Consider empty/whitespace-only strings as empty.
- NON-EMPTY object: at least one field is non-null and non-empty (recursively).
- Numeric operations: only on numeric values; attempt safe conversion from strings, else type_mismatch.

Counting, dedup, scope:
- Unit of counting = smallest coherent JSON object matching the requirement subject.
- Deduplicate by (unit path + salient subkeys) to avoid double counting.
- If scope is unspecified, evaluate at product/root first; if inconclusive, extend to all sub-units/components. Record ambiguity if relevant.

Ignore irrelevant noise:
- Ignore labels/notes/long descriptions unless the requirement explicitly targets them.

Errors (use these labels):
- subject_not_found, ambiguous_scope, placeholder_only, type_mismatch, insufficient_evidence, parse_failure.
"""

descriptor_validation = """
**Descriptor (JSON to evaluate)**
content:
{{content}}

Descriptor processing:
- Build a normalized index (path -> value) for all objects and arrays.
- Identify evidence candidates by matching subject terms to normalized keys and object shapes.
- Treat present-but-empty objects as placeholders (NOT NON-EMPTY).
- For lists, each element can be a counting unit if it independently matches the subject.
"""

policy_validation = """
**Policy**
The policy states:
{{policy}}

Strict evaluation pipeline:

Step 1 — ReadPolicy
- Split into atomic requirements. Extract quantities/thresholds and logical connectives (ALL/ANY). Note any explicit scope.

Step 2 — Canonize
- Canonical record per requirement:
  {subject_terms[], operator, threshold?, quantifier?, logic(ALL|ANY), scope_hint?, exceptions?}
- Operators: EXISTS, NOT_EXISTS, NON_EMPTY, ==, !=, >=, <=, CONTAINS, MATCHES.
- Quantifiers: ANY, AT_LEAST_N, EXACTLY_N, ALL.
- Heuristics:
  - “must define/include/provide” → EXISTS (+ optionally NON_EMPTY).
  - “must not” → NOT_EXISTS.
  - “at least N/≥N/one or more/any” → AT_LEAST_N with N (default 1 if implied).
  - “exactly N” → EXACTLY_N.

Step 3 — SetScope
- If scope_hint is absent, start at product/root; else use scope_hint.
- If still ambiguous, extend to all plausible sub-units/components that could host the subject. Record ambiguous_scope if multiple interpretations exist.

Step 4 — LocateEvidence
- Use the descriptor index to collect candidate units for each requirement.
- Ignore noisy/descriptive-only sections unless directly targeted by the subject_terms[].

Step 5 — Evaluate
- EXISTS: satisfied if ≥1 matching unit exists.
- NOT_EXISTS: satisfied if no matching unit exists.
- NON_EMPTY: satisfied if ≥1 unit is NON-EMPTY (not placeholder_only).
- ==, !=, >=, <=, CONTAINS, MATCHES: evaluate per unit; for numeric ops, require numeric values or mark type_mismatch.
- Apply quantifiers and logic (ALL/ANY) over deduplicated units.

Step 6 — Decide
- If any requirement is violated → satisfiesPolicy=false.
- If all are satisfied → satisfiesPolicy=true.
- If unresolved indeterminacy prevents a safe positive decision → satisfiesPolicy=false and list concise reasons.

Step 7 — Output
- Return ONLY the fixed JSON result (schema provided elsewhere). No extra text.
"""

json_response = """
Create an answer that is a JSON structured like this.
YOU MUST RETURN ONLY THIS JSON, no other information.
The structure is fixed, and all fields are mandatory:

{
"satisfiesPolicy": boolean
"details": {
"suggestion": string,
"elapsedTime": double
},
"errors": array[string]
}
"""
