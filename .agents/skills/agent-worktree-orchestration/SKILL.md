---
name: agent-worktree-orchestration
description: Coordinate coding agents using isolated Git worktrees and explicit race, comparison, or sequential handoff strategies. Use when implementing alternatives or splitting coding work across agents, branches, or sessions.
---

# Agent worktree orchestration

Give each concurrent writer an isolated branch and worktree. Git records implementation state; acceptance checks determine which result is useful.

## Choose a strategy

Read [strategy selection](references/strategy-selection.md) before choosing among racing candidates, comparing alternatives, or a sequential pipeline.

Racing duplicates work and costs the sum of participants. It is useful when time to a passing candidate matters and that cost is acceptable. Comparing candidates needs a shared rubric. A pipeline suits dependent stages.

The first success, shortest diff, or fewest iterations is not proof of best quality. Do not describe such a heuristic as an independent consensus review.

## Prepare ownership

Record repository, base commit, selected agents and models, per-agent worktree, allowed paths, acceptance checks, and budgets. Respect the user's chosen model; do not substitute silently.

Use separate worktrees for concurrent writers. Verify each worktree's branch and status before launch. Preserve unrelated dirty work and existing branches.

Within a sequential pipeline, hand over an exact revision or scoped diff with validation evidence. Keep only one writer active in a shared worktree at a time.

## Collect and integrate

Collect both successful and failed results. A partial failure must not discard another agent's useful artifact. Avoid abruptly terminating a writer without a supported cancellation/checkpoint mechanism.

For each result, retain revision, changed paths, acceptance evidence, unresolved concerns, elapsed work, and cost when measured. Do not invent missing token costs.

Use one integration owner. Review selected changes, handle conflicts deliberately, then rerun acceptance checks on the combined revision.

## Preserve and clean up

Update the project continuation record before changing lanes. Identify unintegrated commits and the exact next action.

Remove only worktrees owned by this run and verified to have no unrecovered work. Never apply blanket force cleanup to other sessions. Publishing branches, opening PRs, and merging remain separately scoped actions.
