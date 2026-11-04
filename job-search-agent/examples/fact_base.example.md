---
description: Example fact base -- replace with your own before running phase01/phase04 for real. Fictional person, fictional numbers.
---
# Verified Fact Base (example)

This is the single source of truth the proof-factory and application-engine
agents draw from instead of inventing or loosely paraphrasing claims about
you. Three tags, used consistently:

- **[VERIFIED]** -- stated directly by you. Safe to quote verbatim.
- **[NEEDS INPUT]** -- a placeholder; never used in an outward-facing draft.
- **[RECONSTRUCTED]** -- inferred narrative; needs a gut-check before quoting.

Any automation here should only pull from **[VERIFIED]** lines for anything
a reader could later fact-check against you directly.

---

## Example Corp -- Senior Product Manager (fictional, replace this file)

- [VERIFIED] Cut checkout latency 30% by shipping a caching layer in front
  of the pricing service.
- [VERIFIED] Grew weekly active users 15% through three structured
  experiments on the onboarding flow.
- [NEEDS INPUT] Exact revenue impact of the Q3 pricing experiment -- not
  yet measured.

This file ships as a placeholder so the repo runs out of the box without
exposing anyone's real resume data. Swap in your own facts, tagged
honestly, before pointing phase01 or phase04 at a real job search.
