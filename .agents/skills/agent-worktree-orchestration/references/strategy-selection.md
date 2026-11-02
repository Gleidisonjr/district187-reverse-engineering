# Selecting a coordination strategy

| Strategy | Useful when | Evidence needed | Main cost or failure mode |
| --- | --- | --- | --- |
| Independent tasks | Outputs can be integrated with clear ownership | Each task's checks, then combined checks | Interface drift or overlapping changes |
| Race | Time to a passing candidate matters | Same acceptance bar for every candidate | Total work can exceed the winner's work |
| Compare alternatives | Several approaches need evaluation | Shared inputs, rubric, and reproducible candidate results | Choosing a convenient proxy for quality |
| Sequential pipeline | Each stage depends on the previous result | Exact handoff revision and stage acceptance | A later stage invalidating earlier checks |

Ralph Starter's inspected implementation supports race, consensus, and pipeline. In revision `ee9c7946c386bb9cecc4001a052e29ffa53f8f9a`, the implementation called consensus selects among successful results using iteration count. Its header mentions an LLM judge, but the selection code does not use one. Follow the implementation when explaining behavior.

This generic workflow requires an explicit selection rubric instead of treating a strategy name as evidence of correctness. Keep useful losing branches until their work is recovered or explicitly disposable; do not copy forced blanket cleanup into a shared workspace.
