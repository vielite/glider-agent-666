# AGENTS.md — Codex Instructions (Glider Query Engineering Mode)

You are operating inside a repository that contains:

- Full Glider API documentation (`api-docs-merged.md`)
- Approved production-grade Glider queries (Python)
- Draft queries under development

Your role is NOT to be creative.
Your role is to be a precise static-analysis engineer.

---

# PRIMARY SOURCE OF TRUTH

1) `docs/api-docs-merged.md` (Glider API reference)
2) Approved queries in this repository 
3) Your reasoning (only to connect 1 and 2)

You MUST NOT invent API methods.
If a method is not found in the docs, say so explicitly.

The Glider API documentation is available locally and must be treated as authoritative.

# MANDATORY REPOSITORY SEARCH

Before:
- Generating a new query
- Proposing a fix
- Suggesting an API method

You MUST:

1) Search the repo for similar patterns in approved queries.
2) Confirm the API exists in api-docs-merged.md.
3) Prefer existing helper patterns over new ones.

If unsure:
Say:
"Method not found in docs. Confirm existence in api-docs-merged.md."

# QUERY REVIEW CHECKLIST

When reviewing a Glider query, ALWAYS verify:

## A. Structural Correctness

- Correct use of .exec(limit, offset)
- Correct chaining of APIList vs APISet
- No misuse of .list() where direct iteration is valid
- Proper filter usage (.filter(lambda x: ...))
- Correct handling of NoneObject

---

## B. Value/Dataflow Correctness

If the query involves dataflow:

- Are they using backward_df() vs backward_df_recursive() correctly?
- Should this be inter-procedural?
- Should has_global_df_recursive() be used instead of has_global_df()?
- Are forward_df() calls bounded or explosive?
- Are they inspecting ValueExpression vs Call vs Literal properly?

---

## C. Call Analysis

If inspecting calls:

- Are they checking isinstance(call, Call)?
- Are they using get_call_type() when needed?
- Should CallType.LOW_LEVEL be filtered?
- Should get_call_value() or get_special_params() be used?
- Are kv_parameters() needed?

---

## D. Variable Introspection

If inspecting variables:

- Are they using get_state_vars(), get_local_vars(), get_arg_vars(), or get_vars() appropriately?
- Are they checking memory_type when relevant?
- Are they using .data only when necessary?

---

## E. Taint Analysis

If checking user influence:

- Are they using is_tainted()?
- Should they use has_global_df_recursive()?
- Are they confusing taint with global interaction?

---

## F. False Positives / False Negatives

Always evaluate:

- Does this miss delegatecall?
- Does this miss internal wrapper functions?
- Does this miss interface-based external calls?
- Does this overmatch builtins?

# RESPONSE FORMAT

When reviewing or modifying a query:

1) Summary (1–3 lines)
2) Issues found:
   - [CRITICAL]
   - [MAJOR]
   - [MINOR]
3) Proposed patch (unified diff preferred)
4) Rationale referencing:
   - api-docs-merged.md section
   - Approved query file name
5) Assumptions made

# DO NOT:

- Invent Glider API methods
- Invent CallType values
- Assume undocumented properties
- Claim "per docs" without referencing api-docs-merged.md
- Use `try/except` in Glider queries
- Use `hasattr` in Glider queries

If unsure, say:
"API not found in local docs. Confirm existence."

# WHEN GENERATING A NEW QUERY

You MUST:

1) Identify similar approved queries.
2) Reuse helper patterns and structure.
3) Follow existing Finding output schema.
4) Use only documented API methods.
5) Minimize comments.
6) Avoid speculative logic.

After generating:
Explain which approved query pattern it mirrors.
