---
name: gauntlet-loop
description: Improve a product or artifact through repeated construction, independent critique, measured comparison, and regression checks. Use for sustained iteration when a single implementation pass cannot establish the required quality.
---

# Gauntlet loop

Start with a baseline and explicit quality bar. The builder produces candidates; independent evaluation determines whether the evidence supports keeping them.

## Establish the bar

Translate the desired outcome into observable behavior. Record the input, environment, baseline artifact, measurement method, and budgets. Explain where thresholds come from.

Keep technical correctness, runtime evidence, visual judgment, and user acceptance distinct. A green suite establishes only the contracts it exercises.

## Run one useful round

1. Give a builder a bounded change and ownership of affected files.
2. Capture the actual result in the same scenario as the baseline.
3. Ask an independent critic to compare raw artifacts against the specification.
4. Check for regressions and metric gaming.
5. Keep, revise, or reject the candidate using evidence.

Parallel builders need separate worktrees or non-overlapping ownership. Sequence work with dependent outputs. Use the user's selected browser and environment for visual verification; coordinate captures so competing sessions do not distort results.

An expensive result should survive a cheaper diagnostic first. Do not broaden work merely because another iteration is possible.

## Decide the next round

Fix regressions before adding polish. Compare the same inputs, viewport, load, revision, and measurement window. Record unavoidable differences.

Use [a round record](references/round-record.md) to preserve the comparison and next hypothesis. Retain a failed candidate's useful evidence without mixing its changes into the accepted result.

Continue toward acceptance within the agreed scope and budget. If progress stalls, change the hypothesis or run a discriminating experiment.

Stop when the objective is met, the user stops work, an agreed limit is reached, or an actual blocker prevents meaningful progress. Report missing evidence explicitly.
