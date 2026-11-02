---
name: evidence-driven-debugging
description: Investigate and fix defects by reproducing the reported path, comparing hypotheses, and checking runtime behavior. Use for bugs, regressions, intermittent failures, and fixes needing evidence beyond a plausible code change.
---

# Evidence-driven debugging

Follow the exact path the user reported. A passing check on a nearby subsystem does not explain the defect.

## Find a decisive observation

Record the symptom, expected behavior, revision, inputs, and environment. Trace the action through the real UI, API, persisted state, or artifact pipeline.

Reproduce the failure or identify the smallest observation separating the leading explanations. Include a competing explanation for an obvious first guess when evidence is ambiguous.

A page can display stale data while the query is correct. An asset can exist while production imports an older hash. A count can measure events while the user asked about distinct participants.

## Make the check useful

Choose the smallest check exercising the failing behavior. If adding a regression gate, show that it detects the broken state before fixing it. A deliberate negative control can reveal whether the gate reads runtime behavior.

A screenshot, network response, or raw measurement can be decisive. Use the form appropriate to the symptom. Do not replace a visible failure with a claim based only on syntax or a build.

## Fix and verify

Change the cause within scope. Rerun the failure case and nearby affected contracts. Preserve unrelated work, ownership boundaries, and accepted product decisions.

Record the cause, changed behavior, verification command or capture, and material limits in the project's designated bug or continuation record.

If reproduction remains unavailable, distinguish a proposed fix from a verified correction. Timeouts and incomplete measurements remain unknown.
